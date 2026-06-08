#!/usr/bin/env python3
"""
road_surface_test.py

카메라 영상 → Hailo-8 NPU 추론 → 도로/인도 텍스트 출력
다른 제어 없음. 콘솔 출력 전용.

실행:
    python3 road_surface_test.py

HEF 출력 포맷 (best.hef 기준):
    best/conv109           (1, 104, 104, 32)  ← proto 마스크 텐서
    best/format_conversion16  (1, 1, 38, 3549)  ← combined 앵커 텐서
      38 = 4(bbox decoded) + 2(cls logits) + 32(mask coeffs)
      3549 = 52×52 + 26×26 + 13×13  (입력 416×416 기준 전 stride 합)
"""

import sys
import time
from collections import deque

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

# ── 설정 ─────────────────────────────────────────────────────────────────────
HEF_PATH       = "src/ai/hef/best.hef"
NUM_CLASSES    = 2
ROAD_CLASS     = 0
SIDEWALK_CLASS = 1
CONF_THR       = 0.40          # 앵커 신뢰도 임계값
ROI_X          = (0.3, 0.7)   # 화면 가로 30~70%
ROI_Y          = (0.6, 1.0)   # 화면 세로 60~100% (바퀴 앞 기준)
WINDOW_SIZE    = 7             # 시간적 안정화 프레임 수
SW_TRIGGER     = 0.5           # 인도 판정 비율 임계값
MAX_MASKS      = 60            # 클래스당 마스크 재구성 최대 개수 (속도 제한)
# ─────────────────────────────────────────────────────────────────────────────

_PROTO_KEY    = "best/conv109"
_COMBINED_KEY = "best/format_conversion16"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50.0, 50.0)))


# ── 후처리: combined 텐서 → 픽셀 class_map ───────────────────────────────────
def _postprocess(res: dict, input_h: int, input_w: int):
    """
    Returns:
        class_map  (input_h, input_w) int32   — 클래스 id, 미검출=-1
        conf_map   (input_h, input_w) float32 — 픽셀별 신뢰도
    """
    # proto: (1, proto_h, proto_w, 32) → (proto_h, proto_w, 32)
    proto     = res[_PROTO_KEY][0]
    proto_h, proto_w = proto.shape[:2]
    proto_flat = proto.reshape(-1, 32)          # (proto_h*proto_w, 32)

    # combined: (1, 1, 38, 3549) → (3549, 38)
    # 38 = [0:4] bbox_decoded | [4:6] cls_logits | [6:38] mask_coeffs
    data      = res[_COMBINED_KEY][0, 0].T      # (3549, 38)
    cls_raw   = data[:, 4:6]                    # (3549, 2)
    mask_coef = data[:, 6:38]                   # (3549, 32)

    cls_scores = _sigmoid(cls_raw)              # (3549, 2)
    max_scores = cls_scores.max(axis=1)         # (3549,)
    cls_ids    = cls_scores.argmax(axis=1)      # (3549,)

    class_map = np.full((input_h, input_w), -1, dtype=np.int32)
    conf_map  = np.zeros((input_h, input_w), dtype=np.float32)
    accum     = np.zeros((NUM_CLASSES, input_h, input_w), dtype=np.float32)

    for cls_id in range(NUM_CLASSES):
        mask_cls = (cls_ids == cls_id) & (max_scores > CONF_THR)
        if not mask_cls.any():
            continue

        scores_here = max_scores[mask_cls]
        coeffs_here = mask_coef[mask_cls]

        # 신뢰도 높은 순 MAX_MASKS개만 처리 (성능 제한)
        if len(scores_here) > MAX_MASKS:
            top = np.argpartition(scores_here, -MAX_MASKS)[-MAX_MASKS:]
            coeffs_here = coeffs_here[top]

        # 마스크 재구성: (N, 32) @ (32, proto_h*proto_w) → (N, proto_h, proto_w)
        raw = _sigmoid(coeffs_here @ proto_flat.T).reshape(-1, proto_h, proto_w)

        for mask in raw:
            mask_up = cv2.resize(mask, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
            accum[cls_id] = np.maximum(accum[cls_id], mask_up)

    valid = accum.max(axis=0) > CONF_THR
    class_map[valid] = accum[:, valid].argmax(axis=0)
    conf_map[valid]  = accum[:, valid].max(axis=0)

    return class_map, conf_map


# ── ROI 픽셀 다수결 ───────────────────────────────────────────────────────────
def _classify_roi(class_map: np.ndarray, conf_map: np.ndarray):
    h, w = class_map.shape
    x1, x2 = int(w * ROI_X[0]), int(w * ROI_X[1])
    y1, y2 = int(h * ROI_Y[0]), int(h * ROI_Y[1])

    roi_cls  = class_map[y1:y2, x1:x2]
    roi_conf = conf_map[y1:y2, x1:x2]

    road_mask = (roi_cls == ROAD_CLASS)     & (roi_conf > CONF_THR)
    sw_mask   = (roi_cls == SIDEWALK_CLASS) & (roi_conf > CONF_THR)

    road_px = int(road_mask.sum())
    sw_px   = int(sw_mask.sum())

    if road_px == 0 and sw_px == 0:
        return "UNKNOWN", 0.0
    if road_px >= sw_px:
        return "ROAD",     float(roi_conf[road_mask].mean())
    return "SIDEWALK", float(roi_conf[sw_mask].mean())


# ── 시간적 안정화 ─────────────────────────────────────────────────────────────
class _Stabilizer:
    def __init__(self):
        self._buf = deque(maxlen=WINDOW_SIZE)

    def update(self, label: str, conf: float):
        self._buf.append((label, conf))
        n      = len(self._buf)
        sw_cnt = sum(1 for l, _ in self._buf if l in ("SIDEWALK", "UNKNOWN"))
        if sw_cnt / n >= SW_TRIGGER:
            sw_c = [c for l, c in self._buf if l == "SIDEWALK"]
            return "SIDEWALK", float(np.mean(sw_c)) if sw_c else 0.3
        rd_c = [c for l, c in self._buf if l == "ROAD"]
        return "ROAD", float(np.mean(rd_c)) if rd_c else 0.3


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    # 카메라 열기
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

    # HEF 로드
    print(f"HEF 로드 중: {HEF_PATH}")
    hef   = HEF(HEF_PATH)
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

                    # 출력 키 검증
                    dummy = np.zeros((1, input_h, input_w, 3), dtype=np.uint8)
                    dry   = pipeline.infer({info.name: dummy})

                    if _PROTO_KEY not in dry or _COMBINED_KEY not in dry:
                        print("ERROR: 예상 출력 텐서를 찾을 수 없습니다.")
                        print("실제 출력 목록:")
                        for k, v in dry.items():
                            print(f"  {k}: {v.shape}")
                        sys.exit(1)

                    print(f"proto  텐서: {_PROTO_KEY} {dry[_PROTO_KEY].shape}")
                    print(f"combined 텐서: {_COMBINED_KEY} {dry[_COMBINED_KEY].shape}\n")

                    t_prev = time.perf_counter()

                    while True:
                        # 프레임 캡처
                        if is_picam:
                            frame = cam.capture_array("main")
                        else:
                            ret, frame = cam.read()
                            if not ret:
                                continue

                        # 전처리: 리사이즈 + BGR→RGB
                        img = cv2.cvtColor(
                            cv2.resize(frame, (input_w, input_h)),
                            cv2.COLOR_BGR2RGB,
                        )

                        # NPU 추론
                        res = pipeline.infer({info.name: np.expand_dims(img, 0)})

                        # 후처리 → class_map
                        class_map, conf_map = _postprocess(res, input_h, input_w)

                        # ROI 픽셀 다수결
                        raw_label, raw_conf = _classify_roi(class_map, conf_map)

                        # 시간적 안정화
                        label, conf = stabilizer.update(raw_label, raw_conf)

                        # FPS 계산
                        now    = time.perf_counter()
                        fps    = 1.0 / max(now - t_prev, 1e-6)
                        t_prev = now

                        # 콘솔 출력
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
