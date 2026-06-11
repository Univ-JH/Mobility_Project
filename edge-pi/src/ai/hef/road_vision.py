#!/usr/bin/env python3
"""
road_vision.py  --  Pi Camera Module 3 + Hailo-8 NPU
YOLOv8-seg based road / sidewalk segmentation pipeline.

Standalone process: communicates with VisionReceiver via UDP.
UDP message format: "{surface_class},{confidence}"  e.g. "road,0.87" / "sidewalk,0.43"

Usage:
    python3 road_vision.py [--config path/to/road_vision_config.json] [--no-display]

Safety contract (AGENTS.md Fail-Safe):
    UNKNOWN result  ->  treated as SIDEWALK (conservative limit/brake)
    Low confidence  ->  forwarded as-is; state_machine applies VISION_CONFIDENCE_THRESHOLD
"""

import argparse
import json
import logging
import socket
import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from picamera2 import Picamera2
    _PICAM2_OK = True
except ImportError:
    _PICAM2_OK = False

try:
    from hailo_platform import (
        ConfigureParams, FormatType, HEF, HailoStreamInterface,
        InferVStreams, InputVStreamParams, OutputVStreamParams, VDevice,
    )
    _HAILO_OK = True
except ImportError:
    _HAILO_OK = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_log = logging.getLogger("road_vision")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "model": {
        "hef_path": "src/ai/hef/best.hef",
        "num_classes": 2,
        "road_class_id": 0,
        "sidewalk_class_id": 1,
        "confidence_threshold": 0.40,
        "nms_threshold": 0.50,
    },
    "camera": {
        "use_picamera2": True,
        "capture_width": 1280,
        "capture_height": 720,
        "framerate": 30,
    },
    "roi": {"x_ratio": [0.3, 0.7], "y_ratio": [0.6, 1.0]},
    "stabilization": {
        "window_size": 7,
        "sidewalk_trigger_ratio": 0.5,
        "unknown_as_sidewalk": True,
    },
    "udp": {"host": "127.0.0.1", "port": 5005},
    "display": {
        "enabled": True,
        "window_name": "Road Vision - Smart Mobility",
        "alpha_blend": 0.45,
    },
}


def _load_config(path: Optional[Path]) -> dict:
    cfg: dict = {k: v.copy() for k, v in _DEFAULTS.items()}
    if path and path.exists():
        with open(path) as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and k in cfg:
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def _make_grid(h: int, w: int, stride: int) -> np.ndarray:
    yv, xv = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    return (np.stack((xv, yv), axis=-1).reshape(-1, 2) + 0.5) * stride


def _dfl(raw: np.ndarray, reg_max: int = 16) -> np.ndarray:
    """Distributed focal loss decode: (N, 64) -> (N, 4)."""
    n = raw.shape[0]
    weights = np.arange(reg_max, dtype=np.float32)
    x = _softmax(raw.reshape(n, 4, reg_max))
    return (x * weights).sum(axis=-1)


def _dist2bbox(dist: np.ndarray, grid: np.ndarray) -> np.ndarray:
    return np.concatenate([grid - dist[:, :2], grid + dist[:, 2:]], axis=-1)


# ---------------------------------------------------------------------------
# Layer auto-detector
# ---------------------------------------------------------------------------

class LayerAutoDetector:
    """
    Identifies YOLOv8-seg output tensors by their shapes.

    For input (H, W) and num_classes=2:
        stride 8  -> spatial (H/8,  W/8)
        stride 16 -> spatial (H/16, W/16)
        stride 32 -> spatial (H/32, W/32)
        proto     -> spatial (H/4,  W/4),   channels=32
        bbox head -> channels=64  (4 * reg_max=16)
        cls  head -> channels=num_classes
        mask head -> channels=32
    Works for any model input size (e.g., 416, 640).
    """

    _STRIDES = [8, 16, 32]
    _BBOX_CH = 64
    _MASK_CH = 32

    def detect(
        self,
        res: Dict[str, np.ndarray],
        input_h: int,
        input_w: int,
        num_classes: int,
    ) -> Tuple[Optional[str], List[Tuple[str, str, str, int]]]:
        """Returns (proto_name, [(bbox, cls, mask, stride), ...]) sorted by stride."""
        proto_h, proto_w = input_h // 4, input_w // 4
        proto_name: Optional[str] = None
        heads: Dict[int, Dict[str, str]] = {}

        for name, tensor in res.items():
            t = tensor[0] if tensor.ndim == 4 else tensor
            if t.ndim != 3:
                continue
            h, w, c = t.shape

            if c == self._MASK_CH and h == proto_h and w == proto_w:
                proto_name = name
                continue

            for stride in self._STRIDES:
                if h == input_h // stride and w == input_w // stride:
                    if stride not in heads:
                        heads[stride] = {}
                    if c == self._BBOX_CH:
                        heads[stride]["bbox"] = name
                    elif c == num_classes:
                        heads[stride]["cls"] = name
                    elif c == self._MASK_CH:
                        heads[stride]["mask"] = name

        layers: List[Tuple[str, str, str, int]] = []
        for stride in sorted(heads):
            h = heads[stride]
            if "bbox" in h and "cls" in h and "mask" in h:
                layers.append((h["bbox"], h["cls"], h["mask"], stride))
            else:
                _log.warning("Incomplete detection head at stride %d: found=%s", stride, list(h))

        return proto_name, layers


# ---------------------------------------------------------------------------
# Temporal stabilizer
# ---------------------------------------------------------------------------

ROAD = 0
SIDEWALK = 1
UNKNOWN = -1


class TemporalStabilizer:
    """
    Votes over a sliding window of (class_id, confidence) pairs.
    UNKNOWN frames count as SIDEWALK when unknown_as_sidewalk=True (Fail-Safe).
    """

    def __init__(self, window_size: int, sidewalk_trigger_ratio: float, unknown_as_sidewalk: bool):
        self._window: Deque[Tuple[int, float]] = deque(maxlen=window_size)
        self._trigger = sidewalk_trigger_ratio
        self._unk_as_sw = unknown_as_sidewalk

    @property
    def window(self) -> Deque[Tuple[int, float]]:
        return self._window

    def update(self, class_id: int, confidence: float) -> Tuple[int, float]:
        """Push result, return (voted_class, mean_confidence_of_winner)."""
        self._window.append((class_id, confidence))

        road_confs = [c for cls, c in self._window if cls == ROAD]
        sw_confs   = [c for cls, c in self._window if cls == SIDEWALK]
        unk_count  = sum(1 for cls, _ in self._window if cls == UNKNOWN)

        total = len(self._window)
        sw_votes = len(sw_confs) + (unk_count if self._unk_as_sw else 0)

        if sw_votes / total >= self._trigger:
            return SIDEWALK, float(np.mean(sw_confs)) if sw_confs else 0.3
        elif road_confs:
            return ROAD, float(np.mean(road_confs))
        else:
            return UNKNOWN, 0.0


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

def _init_camera(cfg: dict):
    """Returns (camera_object, is_picam2: bool)."""
    disp_w = cfg["camera"]["capture_width"]
    disp_h = cfg["camera"]["capture_height"]
    fps    = cfg["camera"]["framerate"]

    if cfg["camera"]["use_picamera2"] and _PICAM2_OK:
        _log.info("Opening Pi Camera Module 3 via picamera2 (%dx%d @ %dfps)", disp_w, disp_h, fps)
        cam = Picamera2()
        video_cfg = cam.create_video_configuration(
            main={"size": (disp_w, disp_h), "format": "BGR888"},
            controls={"FrameRate": fps},
        )
        cam.configure(video_cfg)
        cam.start()
        time.sleep(0.8)  # allow AE/AWB to settle
        _log.info("Pi Camera ready")
        return cam, True

    if cfg["camera"]["use_picamera2"] and not _PICAM2_OK:
        _log.warning("picamera2 not available, falling back to OpenCV VideoCapture")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open camera (VideoCapture index 0)")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, disp_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, disp_h)
    cap.set(cv2.CAP_PROP_FPS, fps)
    _log.info("OpenCV camera ready")
    return cap, False


def _capture_frame(cam, is_picam: bool) -> Optional[np.ndarray]:
    """Returns BGR uint8 frame or None on failure."""
    if is_picam:
        return cam.capture_array("main")
    ret, frame = cam.read()
    return frame if ret else None


def _release_camera(cam, is_picam: bool) -> None:
    if is_picam:
        cam.stop()
    else:
        cam.release()


# ---------------------------------------------------------------------------
# YOLOv8-seg post-processing
# ---------------------------------------------------------------------------

def _postprocess(
    res: Dict[str, np.ndarray],
    proto_name: str,
    layers: List[Tuple[str, str, str, int]],
    input_h: int,
    input_w: int,
    conf_thr: float,
    nms_thr: float,
    num_classes: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns:
        class_map  (input_h, input_w)  int32   -- class id per pixel, -1 = no detection
        conf_map   (input_h, input_w)  float32 -- confidence per pixel
    """
    proto_h, proto_w = input_h // 4, input_w // 4
    proto = res[proto_name][0]  # (proto_h, proto_w, 32)

    all_bboxes:  List[np.ndarray] = []
    all_scores:  List[np.ndarray] = []
    all_cls_ids: List[np.ndarray] = []
    all_coeffs:  List[np.ndarray] = []

    for bbox_n, cls_n, mask_n, stride in layers:
        bbox_t = res[bbox_n][0]  # (H, W, 64)
        cls_t  = res[cls_n][0]   # (H, W, num_classes)
        mask_t = res[mask_n][0]  # (H, W, 32)
        H, W, _ = bbox_t.shape

        scores = _sigmoid(cls_t.reshape(-1, num_classes))
        max_sc = scores.max(axis=-1)
        cls_id = scores.argmax(axis=-1)

        keep = max_sc > conf_thr
        if not keep.any():
            continue

        dist  = _dfl(bbox_t.reshape(-1, 64)[keep])
        grid  = _make_grid(H, W, stride)[keep]
        boxes = _dist2bbox(dist, grid)

        all_bboxes.append(boxes)
        all_scores.append(max_sc[keep])
        all_cls_ids.append(cls_id[keep])
        all_coeffs.append(mask_t.reshape(-1, 32)[keep])

    class_map = np.full((input_h, input_w), -1, dtype=np.int32)
    conf_map  = np.zeros((input_h, input_w), dtype=np.float32)

    if not all_bboxes:
        return class_map, conf_map

    bboxes  = np.concatenate(all_bboxes)
    scores  = np.concatenate(all_scores)
    cls_ids = np.concatenate(all_cls_ids)
    coeffs  = np.concatenate(all_coeffs)

    xywh = [[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in bboxes]
    idxs = cv2.dnn.NMSBoxes(xywh, scores.tolist(), conf_thr, nms_thr)
    if len(idxs) == 0:
        return class_map, conf_map
    idxs = np.array(idxs).flatten()

    # Accumulate per-class masks
    accum = np.zeros((num_classes, input_h, input_w), dtype=np.float32)
    proto_flat = proto.reshape(-1, 32)  # (proto_h*proto_w, 32)

    for i in idxs:
        cls  = int(cls_ids[i])
        coef = coeffs[i]                               # (32,)
        raw  = coef @ proto_flat.T                     # (proto_h*proto_w,)
        mask = _sigmoid(raw.reshape(proto_h, proto_w))
        mask_up = cv2.resize(mask, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        accum[cls] = np.maximum(accum[cls], mask_up)

    valid = accum.max(axis=0) > conf_thr
    class_map[valid] = accum[:, valid].argmax(axis=0)
    conf_map[valid]  = accum[:, valid].max(axis=0)

    return class_map, conf_map


# ---------------------------------------------------------------------------
# ROI classification
# ---------------------------------------------------------------------------

def _classify_roi(
    class_map: np.ndarray,
    conf_map: np.ndarray,
    roi_x: Tuple[float, float],
    roi_y: Tuple[float, float],
    road_id: int,
    sidewalk_id: int,
    conf_thr: float,
) -> Tuple[int, float]:
    """
    Pixel-majority vote in the center-bottom ROI.
    Returns (class_id, mean_confidence).
    """
    h, w = class_map.shape
    x1, x2 = int(w * roi_x[0]), int(w * roi_x[1])
    y1, y2 = int(h * roi_y[0]), int(h * roi_y[1])

    roi_cls  = class_map[y1:y2, x1:x2]
    roi_conf = conf_map[y1:y2, x1:x2]

    road_mask = (roi_cls == road_id)     & (roi_conf > conf_thr)
    sw_mask   = (roi_cls == sidewalk_id) & (roi_conf > conf_thr)

    road_px = int(road_mask.sum())
    sw_px   = int(sw_mask.sum())

    if road_px == 0 and sw_px == 0:
        return UNKNOWN, 0.0

    if road_px > sw_px:
        return ROAD,     float(roi_conf[road_mask].mean())
    else:
        return SIDEWALK, float(roi_conf[sw_mask].mean())


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

# BGR colors: road=green, sidewalk=red
_SEG_COLORS = {ROAD: (40, 200, 40), SIDEWALK: (40, 40, 220)}
_STATUS_TEXT = {
    ROAD:     ("ROAD",     (40, 220, 40)),
    SIDEWALK: ("SIDEWALK", (40, 40, 220)),
    UNKNOWN:  ("UNKNOWN",  (200, 200, 200)),
}


def _draw_overlay(
    frame: np.ndarray,
    class_map: np.ndarray,
    conf_map: np.ndarray,
    voted_cls: int,
    voted_conf: float,
    roi_x: Tuple[float, float],
    roi_y: Tuple[float, float],
    fps: float,
    conf_thr: float,
    alpha: float,
    window: Deque[Tuple[int, float]],
) -> np.ndarray:
    orig_h, orig_w = frame.shape[:2]

    # Segmentation colour overlay
    seg_overlay = np.zeros_like(frame, dtype=np.uint8)
    conf_up = cv2.resize(conf_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    for cls_id, color in _SEG_COLORS.items():
        cls_mask = cv2.resize(
            (class_map == cls_id).astype(np.uint8),
            (orig_w, orig_h),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)
        valid = cls_mask & (conf_up > conf_thr)
        seg_overlay[valid] = color

    vis = cv2.addWeighted(frame, 1.0, seg_overlay, alpha, 0)

    # ROI box (yellow)
    rx1, rx2 = int(orig_w * roi_x[0]), int(orig_w * roi_x[1])
    ry1, ry2 = int(orig_h * roi_y[0]), int(orig_h * roi_y[1])
    cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 230, 230), 2)
    cv2.putText(vis, "Bike ROI", (rx1 + 4, ry1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 230), 1, cv2.LINE_AA)

    # Status text
    label, lcolor = _STATUS_TEXT.get(voted_cls, _STATUS_TEXT[UNKNOWN])
    cv2.putText(vis, f"STATUS: {label}", (20, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, lcolor, 3, cv2.LINE_AA)
    cv2.putText(vis, f"Conf:{voted_conf:.2f}  FPS:{fps:.1f}", (20, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (240, 240, 240), 2, cv2.LINE_AA)

    # Temporal window indicator (bottom-left strip)
    cell_w, cell_h = 22, 18
    bar_x, bar_y = 20, orig_h - cell_h - 8
    for j, (c, _) in enumerate(window):
        color = _SEG_COLORS.get(c, (160, 160, 160))
        cv2.rectangle(vis,
                      (bar_x + j * (cell_w + 3), bar_y),
                      (bar_x + j * (cell_w + 3) + cell_w, bar_y + cell_h),
                      color, -1)
    cv2.putText(vis, "window", (bar_x, bar_y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    # Legend (top-right)
    leg_x = orig_w - 150
    cv2.rectangle(vis, (leg_x, 15), (leg_x + 14, 30), _SEG_COLORS[ROAD], -1)
    cv2.putText(vis, "Road",     (leg_x + 18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)
    cv2.rectangle(vis, (leg_x, 38), (leg_x + 14, 53), _SEG_COLORS[SIDEWALK], -1)
    cv2.putText(vis, "Sidewalk", (leg_x + 18, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)

    return vis


# ---------------------------------------------------------------------------
# UDP publisher
# ---------------------------------------------------------------------------

class UDPPublisher:
    def __init__(self, host: str, port: int):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._addr = (host, port)

    def send(self, cls_id: int, confidence: float) -> None:
        if cls_id == ROAD:
            cls_str = "road"
        elif cls_id == SIDEWALK:
            cls_str = "sidewalk"
        else:
            cls_str = "unknown"
        try:
            self._sock.sendto(f"{cls_str},{confidence:.3f}".encode(), self._addr)
        except OSError as e:
            _log.debug("UDP send failed: %s", e)

    def close(self) -> None:
        self._sock.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not _HAILO_OK:
        _log.error("hailo_platform not installed. Run on Raspberry Pi 5 with Hailo-8 SDK.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Road Vision -- Pi Camera 3 + Hailo-8 NPU")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).parent / "road_vision_config.json")
    parser.add_argument("--no-display", action="store_true",
                        help="Disable visual window (headless mode)")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    if args.no_display:
        cfg["display"]["enabled"] = False

    # Resolve HEF path (try config path, then sibling of this script)
    hef_path = Path(cfg["model"]["hef_path"])
    if not hef_path.exists():
        hef_path = Path(__file__).parent / "best.hef"
    if not hef_path.exists():
        _log.error("best.hef not found at: %s", hef_path)
        sys.exit(1)

    conf_thr  = cfg["model"]["confidence_threshold"]
    nms_thr   = cfg["model"]["nms_threshold"]
    num_cls   = cfg["model"]["num_classes"]
    road_id   = cfg["model"]["road_class_id"]
    sw_id     = cfg["model"]["sidewalk_class_id"]
    roi_x     = tuple(cfg["roi"]["x_ratio"])
    roi_y     = tuple(cfg["roi"]["y_ratio"])

    stabilizer = TemporalStabilizer(
        cfg["stabilization"]["window_size"],
        cfg["stabilization"]["sidewalk_trigger_ratio"],
        cfg["stabilization"]["unknown_as_sidewalk"],
    )
    publisher = None
    cam, is_picam = None, False
    try:
        publisher = UDPPublisher(cfg["udp"]["host"], cfg["udp"]["port"])

        # Load HEF and resolve input shape
        _log.info("Loading HEF: %s", hef_path)
        hef = HEF(str(hef_path))
        raw_shape = hef.get_input_vstream_infos()[0].shape
        input_h, input_w = (raw_shape[1], raw_shape[2]) if len(raw_shape) == 4 else (raw_shape[0], raw_shape[1])
        input_name = hef.get_input_vstream_infos()[0].name
        _log.info("Model input: %dx%d  name=%s", input_w, input_h, input_name)

        cam, is_picam = _init_camera(cfg)

        with VDevice() as target:
            params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            ng = target.configure(hef, params)[0]
            in_params  = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
            out_params = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

            with ng.activate(ng.create_params()):
                with InferVStreams(ng, in_params, out_params) as pipeline:

                    # Auto-detect output layers via single dry-run
                    _log.info("Auto-detecting output layers...")
                    dummy = np.zeros((1, input_h, input_w, 3), dtype=np.uint8)
                    dry = pipeline.infer({input_name: dummy})

                    detector = LayerAutoDetector()
                    proto_name, layers = detector.detect(dry, input_h, input_w, num_cls)

                    if proto_name is None or len(layers) == 0:
                        _log.error(
                            "Layer detection failed. Available outputs: %s",
                            [(k, v.shape) for k, v in dry.items()],
                        )
                        sys.exit(1)

                    _log.info("Proto: %s", proto_name)
                    for bn, cn, mn, s in layers:
                        _log.info("  stride=%-2d | bbox=%-35s cls=%-35s mask=%s", s, bn, cn, mn)

                    _log.info("Inference loop started. Press 'q' to quit.")
                    t_prev = time.perf_counter()

                    while True:
                        frame = _capture_frame(cam, is_picam)
                        if frame is None:
                            _log.warning("Dropped frame, retrying...")
                            continue

                        # Preprocess: resize + BGR->RGB
                        img_rgb = cv2.cvtColor(
                            cv2.resize(frame, (input_w, input_h)),
                            cv2.COLOR_BGR2RGB,
                        )
                        input_tensor = np.expand_dims(img_rgb, axis=0)

                        # NPU inference
                        res = pipeline.infer({input_name: input_tensor})

                        # Post-process segmentation
                        class_map, conf_map = _postprocess(
                            res, proto_name, layers,
                            input_h, input_w, conf_thr, nms_thr, num_cls,
                        )

                        # ROI pixel-vote (center-bottom = bicycle reference point)
                        raw_cls, raw_conf = _classify_roi(
                            class_map, conf_map, roi_x, roi_y,
                            road_id, sw_id, conf_thr,
                        )

                        # Temporal stabilization window vote
                        voted_cls, voted_conf = stabilizer.update(raw_cls, raw_conf)

                        # Publish to VisionReceiver
                        publisher.send(voted_cls, voted_conf)

                        # FPS
                        now = time.perf_counter()
                        fps = 1.0 / max(now - t_prev, 1e-6)
                        t_prev = now

                        if cfg["display"]["enabled"]:
                            vis = _draw_overlay(
                                frame, class_map, conf_map,
                                voted_cls, voted_conf,
                                roi_x, roi_y, fps, conf_thr,
                                cfg["display"]["alpha_blend"],
                                stabilizer.window,
                            )
                            cv2.imshow(cfg["display"]["window_name"], vis)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                break
                        else:
                            cls_str = {ROAD: "ROAD", SIDEWALK: "SIDEWALK"}.get(voted_cls, "UNKNOWN")
                            _log.info("state=%-8s conf=%.2f fps=%.1f", cls_str, voted_conf, fps)

    finally:
        if cam is not None:
            _release_camera(cam, is_picam)
        if publisher is not None:
            publisher.close()
        if cfg["display"]["enabled"]:
            cv2.destroyAllWindows()
        _log.info("Shutdown complete.")


if __name__ == "__main__":
    main()
