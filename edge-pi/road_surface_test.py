#!/usr/bin/env python3
"""
road_surface_test.py

카메라 영상 → Hailo-8 NPU 추론 → 도로/인도 텍스트 출력
다른 제어 없음. 콘솔 출력 전용.

실행:
    python3 road_surface_test.py
"""

import sys
import time

import cv2
import numpy as np

try:
    from picamera2 import Picamera2
    _PICAM_OK = True
except ImportError:
    _PICAM_OK = False

from hailo_platform import (
    ConfigureParams, FormatType, HEF, HailoStreamInterface,
    InferVStreams, InputVStreamParams, OutputVStreamParams, VDevice,
)

# ── 설정 ────────────────────────────────────────────────────────────────────
HEF_PATH        = "src/ai/hef/best.hef"
NUM_CLASSES     = 2
ROAD_CLASS      = 0
SIDEWALK_CLASS  = 1
CONF_THR        = 0.40
NMS_THR         = 0.50
ROI_X           = (0.3, 0.7)   # 화면 가로 30~70%
ROI_Y           = (0.6, 1.0)   # 화면 세로 60~100% (바퀴 앞 기준)

# 시간적 안정화 윈도우 (연속 N프레임 다수결)
WINDOW_SIZE     = 7
SW_TRIGGER      = 0.5   # 인도 판정 비율 임계값
# ─────────────────────────────────────────────────────────────────────────────


# ── 수학 헬퍼 ────────────────────────────────────────────────────────────────
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))

def _softmax(x):
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)

def _make_grid(h, w, stride):
    yv, xv = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    return (np.stack((xv, yv), axis=-1).reshape(-1, 2) + 0.5) * stride

def _dfl(raw, reg_max=16):
    n = raw.shape[0]
    x = _softmax(raw.reshape(n, 4, reg_max))
    return (x * np.arange(reg_max, dtype=np.float32)).sum(axis=-1)

def _dist2bbox(dist, grid):
    return np.concatenate([grid - dist[:, :2], grid + dist[:, 2:]], axis=-1)
# ─────────────────────────────────────────────────────────────────────────────


# ── 출력 레이어 자동 탐지 ────────────────────────────────────────────────────
def _detect_layers(res, input_h, input_w, num_classes):
    """
    YOLOv8-seg 출력 텐서 이름을 shape으로 자동 탐지.
    Returns (proto_name, [(bbox_name, cls_name, mask_name, stride), ...])
    """
    proto_h, proto_w = input_h // 4, input_w // 4
    BBOX_CH, MASK_CH = 64, 32

    proto_name = None
    heads = {}

    for name, tensor in res.items():
        t = tensor[0] if tensor.ndim == 4 else tensor
        if t.ndim != 3:
            continue
        h, w, c = t.shape

        if c == MASK_CH and h == proto_h and w == proto_w:
            proto_name = name
            continue

        for stride in [8, 16, 32]:
            if h == input_h // stride and w == input_w // stride:
                heads.setdefault(stride, {})
                if c == BBOX_CH:
                    heads[stride]["bbox"] = name
                elif c == num_classes:
                    heads[stride]["cls"] = name
                elif c == MASK_CH:
                    heads[stride]["mask"] = name

    layers = []
    for stride in sorted(heads):
        h = heads[stride]
        if "bbox" in h and "cls" in h and "mask" in h:
            layers.append((h["bbox"], h["cls"], h["mask"], stride))

    return proto_name, layers
# ─────────────────────────────────────────────────────────────────────────────


# ── 세그멘테이션 후처리 ──────────────────────────────────────────────────────
def _postprocess(res, proto_name, layers, input_h, input_w):
    proto_h, proto_w = input_h // 4, input_w // 4
    proto = res[proto_name][0]   # (proto_h, proto_w, 32)

    all_bboxes, all_scores, all_cls, all_coeffs = [], [], [], []

    for bbox_n, cls_n, mask_n, stride in layers:
        bbox_t = res[bbox_n][0]   # (H, W, 64)
        cls_t  = res[cls_n][0]    # (H, W, num_classes)
        mask_t = res[mask_n][0]   # (H, W, 32)
        H, W, _ = bbox_t.shape

        scores = _sigmoid(cls_t.reshape(-1, NUM_CLASSES))
        max_sc = scores.max(axis=-1)
        cls_id = scores.argmax(axis=-1)

        keep = max_sc > CONF_THR
        if not keep.any():
            continue

        grid  = _make_grid(H, W, stride)[keep]
        dist  = _dfl(bbox_t.reshape(-1, 64)[keep])
        boxes = _dist2bbox(dist, grid)

        all_bboxes.append(boxes)
        all_scores.append(max_sc[keep])
        all_cls.append(cls_id[keep])
        all_coeffs.append(mask_t.reshape(-1, 32)[keep])

    class_map = np.full((input_h, input_w), -1, dtype=np.int32)
    conf_map  = np.zeros((input_h, input_w), dtype=np.float32)

    if not all_bboxes:
        return class_map, conf_map

    bboxes  = np.concatenate(all_bboxes)
    scores  = np.concatenate(all_scores)
    cls_ids = np.concatenate(all_cls)
    coeffs  = np.concatenate(all_coeffs)

    xywh = [[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in bboxes]
    idxs = cv2.dnn.NMSBoxes(xywh, scores.tolist(), CONF_THR, NMS_THR)
    if len(idxs) == 0:
        return class_map, conf_map
    idxs = np.array(idxs).flatten()

    accum = np.zeros((NUM_CLASSES, input_h, input_w), dtype=np.float32)
    proto_flat = proto.reshape(-1, 32)

    for i in idxs:
        cls   = int(cls_ids[i])
        raw   = coeffs[i] @ proto_flat.T
        mask  = _sigmoid(raw.reshape(proto_h, proto_w))
        mask_up = cv2.resize(mask, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        accum[cls] = np.maximum(accum[cls], mask_up)

    valid = accum.max(axis=0) > CONF_THR
    class_map[valid] = accum[:, valid].argmax(axis=0)
    conf_map[valid]  = accum[:, valid].max(axis=0)

    return class_map, conf_map
# ─────────────────────────────────────────────────────────────────────────────


# ── ROI 판별 ─────────────────────────────────────────────────────────────────
def _classify_roi(class_map, conf_map):
    h, w = class_map.shape
    x1, x2 = int(w * ROI_X[0]), int(w * ROI_X[1])
    y1, y2 = int(h * ROI_Y[0]), int(h * ROI_Y[1])

    roi_cls  = class_map[y1:y2, x1:x2]
    roi_conf = conf_map[y1:y2, x1:x2]

    road_px = int(((roi_cls == ROAD_CLASS)     & (roi_conf > CONF_THR)).sum())
    sw_px   = int(((roi_cls == SIDEWALK_CLASS) & (roi_conf > CONF_THR)).sum())

    if road_px == 0 and sw_px == 0:
        return "UNKNOWN", 0.0
    if road_px >= sw_px:
        mean_conf = float(roi_conf[(roi_cls == ROAD_CLASS) & (roi_conf > CONF_THR)].mean())
        return "ROAD", mean_conf
    else:
        mean_conf = float(roi_conf[(roi_cls == SIDEWALK_CLASS) & (roi_conf > CONF_THR)].mean())
        return "SIDEWALK", mean_conf
# ─────────────────────────────────────────────────────────────────────────────


# ── 안정화 윈도우 ─────────────────────────────────────────────────────────────
class _Stabilizer:
    def __init__(self):
        from collections import deque
        self._buf = deque(maxlen=WINDOW_SIZE)

    def update(self, label, conf):
        self._buf.append((label, conf))
        n      = len(self._buf)
        sw_cnt = sum(1 for l, _ in self._buf if l in ("SIDEWALK", "UNKNOWN"))
        if sw_cnt / n >= SW_TRIGGER:
            sw_confs = [c for l, c in self._buf if l == "SIDEWALK"]
            return "SIDEWALK", float(np.mean(sw_confs)) if sw_confs else 0.3
        rd_confs = [c for l, c in self._buf if l == "ROAD"]
        return "ROAD", float(np.mean(rd_confs)) if rd_confs else 0.3
# ─────────────────────────────────────────────────────────────────────────────


def main():
    # ── 카메라 열기 ──────────────────────────────────────────────────────────
    if _PICAM_OK:
        cam = Picamera2()
        cam.configure(cam.create_video_configuration(
            main={"size": (1280, 720), "format": "BGR888"},
            controls={"FrameRate": 30},
        ))
        cam.start()
        time.sleep(0.8)
        is_picam = True
        print("카메라: Pi Camera Module 3 (picamera2)")
    else:
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            print("ERROR: 카메라를 열 수 없습니다.")
            sys.exit(1)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        is_picam = False
        print("카메라: OpenCV VideoCapture")

    # ── HEF 로드 ─────────────────────────────────────────────────────────────
    print(f"HEF 로드 중: {HEF_PATH}")
    hef = HEF(HEF_PATH)
    info  = hef.get_input_vstream_infos()[0]
    shape = info.shape
    input_h, input_w = (shape[1], shape[2]) if len(shape) == 4 else (shape[0], shape[1])
    print(f"모델 입력 크기: {input_w}x{input_h}")
    print("추론 시작. 종료: Ctrl+C\n")

    stabilizer = _Stabilizer()

    try:
        with VDevice() as target:
            params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            ng     = target.configure(hef, params)[0]
            in_p   = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
            out_p  = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

            with ng.activate(ng.create_params()):
                with InferVStreams(ng, in_p, out_p) as pipeline:

                    # 출력 레이어 이름 자동 탐지 (dry-run 1회)
                    dummy = np.zeros((1, input_h, input_w, 3), dtype=np.uint8)
                    dry   = pipeline.infer({info.name: dummy})
                    proto_name, layers = _detect_layers(dry, input_h, input_w, NUM_CLASSES)

                    if proto_name is None or not layers:
                        print("ERROR: 출력 레이어 자동 탐지 실패.")
                        print("출력 텐서 목록:", [(k, v.shape) for k, v in dry.items()])
                        sys.exit(1)

                    t_prev = time.perf_counter()

                    while True:
                        # 프레임 캡처
                        if is_picam:
                            frame = cam.capture_array("main")
                        else:
                            ret, frame = cam.read()
                            if not ret:
                                continue

                        # 전처리 (리사이즈 + BGR→RGB)
                        img = cv2.cvtColor(
                            cv2.resize(frame, (input_w, input_h)),
                            cv2.COLOR_BGR2RGB,
                        )

                        # NPU 추론
                        res = pipeline.infer({info.name: np.expand_dims(img, 0)})

                        # 세그멘테이션 후처리
                        class_map, conf_map = _postprocess(res, proto_name, layers, input_h, input_w)

                        # ROI 픽셀 다수결
                        raw_label, raw_conf = _classify_roi(class_map, conf_map)

                        # 시간적 안정화
                        label, conf = stabilizer.update(raw_label, raw_conf)

                        # FPS
                        now    = time.perf_counter()
                        fps    = 1.0 / max(now - t_prev, 1e-6)
                        t_prev = now

                        # ── 콘솔 출력 ────────────────────────────────────────
                        print(f"[{label:<8}]  신뢰도: {conf:.3f}  FPS: {fps:5.1f}")

    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        if is_picam:
            cam.stop()
        else:
            cam.release()


if __name__ == "__main__":
    main()
