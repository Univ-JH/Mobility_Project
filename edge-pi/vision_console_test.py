#!/usr/bin/env python3
"""
vision_console_test.py — inference-only console monitor

Runs the Hailo-8 NPU road/sidewalk segmentation pipeline and prints
results to stdout. No servo, no MQTT, no UDP, no display window.

Usage:
    python3 vision_console_test.py
    python3 vision_console_test.py --config src/ai/hef/road_vision_config.json
    python3 vision_console_test.py --no-stabilize   # raw per-frame output
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Reuse all inference helpers from road_vision — no duplication
from src.ai.hef.road_vision import (
    ROAD, SIDEWALK, UNKNOWN,
    LayerAutoDetector,
    TemporalStabilizer,
    _HAILO_OK,
    _classify_roi,
    _init_camera,
    _capture_frame,
    _load_config,
    _postprocess,
    _release_camera,
)

try:
    from hailo_platform import (
        ConfigureParams, FormatType, HEF, HailoStreamInterface,
        InferVStreams, InputVStreamParams, OutputVStreamParams, VDevice,
    )
except ImportError:
    pass  # _HAILO_OK already False

_LABEL = {ROAD: "ROAD", SIDEWALK: "SIDEWALK", UNKNOWN: "UNKNOWN"}


def _print_result(label: str, conf: float, fps: float, raw_label: str, raw_conf: float) -> None:
    print(
        f"[{label:<8}]  conf={conf:.3f}  fps={fps:5.1f}"
        f"  (raw: {raw_label:<8} {raw_conf:.3f})"
    )


def main() -> None:
    if not _HAILO_OK:
        print("ERROR: hailo_platform not installed. Run on Raspberry Pi 5 with Hailo-8 SDK.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Vision console test — inference output only")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).parent / "src/ai/hef/road_vision_config.json")
    parser.add_argument("--no-stabilize", action="store_true",
                        help="Print raw per-frame result without temporal window voting")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    cfg["display"]["enabled"] = False  # never show window

    conf_thr = cfg["model"]["confidence_threshold"]
    nms_thr  = cfg["model"]["nms_threshold"]
    num_cls  = cfg["model"]["num_classes"]
    road_id  = cfg["model"]["road_class_id"]
    sw_id    = cfg["model"]["sidewalk_class_id"]
    roi_x    = tuple(cfg["roi"]["x_ratio"])
    roi_y    = tuple(cfg["roi"]["y_ratio"])

    stabilizer = TemporalStabilizer(
        cfg["stabilization"]["window_size"],
        cfg["stabilization"]["sidewalk_trigger_ratio"],
        cfg["stabilization"]["unknown_as_sidewalk"],
    ) if not args.no_stabilize else None

    hef_path = Path(cfg["model"]["hef_path"])
    if not hef_path.exists():
        hef_path = Path(__file__).parent / "src/ai/hef/best.hef"
    if not hef_path.exists():
        print(f"ERROR: best.hef not found at: {hef_path}")
        sys.exit(1)

    print(f"Loading HEF: {hef_path}")
    hef = HEF(str(hef_path))
    raw_shape  = hef.get_input_vstream_infos()[0].shape
    input_h, input_w = (raw_shape[1], raw_shape[2]) if len(raw_shape) == 4 else (raw_shape[0], raw_shape[1])
    input_name = hef.get_input_vstream_infos()[0].name
    print(f"Model input: {input_w}x{input_h}  stabilize={'off' if args.no_stabilize else 'on'}")

    cam, is_picam = _init_camera(cfg)
    print("Camera ready. Press Ctrl+C to stop.\n")

    try:
        with VDevice() as target:
            params   = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            ng       = target.configure(hef, params)[0]
            in_p     = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
            out_p    = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

            with ng.activate(ng.create_params()):
                with InferVStreams(ng, in_p, out_p) as pipeline:

                    # Dry-run to detect output layer names/shapes
                    dummy      = np.zeros((1, input_h, input_w, 3), dtype=np.uint8)
                    dry        = pipeline.infer({input_name: dummy})
                    detector   = LayerAutoDetector()
                    proto_name, layers = detector.detect(dry, input_h, input_w, num_cls)

                    if proto_name is None or not layers:
                        print("ERROR: Layer auto-detection failed.")
                        print("Available outputs:", [(k, v.shape) for k, v in dry.items()])
                        sys.exit(1)

                    t_prev = time.perf_counter()

                    while True:
                        frame = _capture_frame(cam, is_picam)
                        if frame is None:
                            continue

                        img_rgb = cv2.cvtColor(
                            cv2.resize(frame, (input_w, input_h)),
                            cv2.COLOR_BGR2RGB,
                        )
                        res = pipeline.infer({input_name: np.expand_dims(img_rgb, 0)})

                        class_map, conf_map = _postprocess(
                            res, proto_name, layers,
                            input_h, input_w, conf_thr, nms_thr, num_cls,
                        )

                        raw_cls, raw_conf = _classify_roi(
                            class_map, conf_map, roi_x, roi_y,
                            road_id, sw_id, conf_thr,
                        )

                        if stabilizer:
                            out_cls, out_conf = stabilizer.update(raw_cls, raw_conf)
                        else:
                            out_cls, out_conf = raw_cls, raw_conf

                        now   = time.perf_counter()
                        fps   = 1.0 / max(now - t_prev, 1e-6)
                        t_prev = now

                        _print_result(
                            _LABEL.get(out_cls, "UNKNOWN"), out_conf, fps,
                            _LABEL.get(raw_cls, "UNKNOWN"), raw_conf,
                        )

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        _release_camera(cam, is_picam)


if __name__ == "__main__":
    main()
