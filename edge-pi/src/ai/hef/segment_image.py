#!/usr/bin/env python3
"""
segment_image.py -- Hailo-8 NPU를 이용한 정적 이미지 도로/인도 세그멘테이션

Usage:
    python3 segment_image.py image1.jpg image2.png ...
    python3 segment_image.py *.jpg --show
    python3 segment_image.py test.jpg --out-dir ./results --conf 0.45

출력: {원본파일명}_seg.jpg  (세그멘테이션 오버레이 이미지)
Fail-Safe: 감지 없음 / 불확실 → SIDEWALK(인도) 처리
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

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
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_log = logging.getLogger("segment_image")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROAD     = 0
SIDEWALK = 1
UNKNOWN  = -1

_SEG_COLORS = {ROAD: (40, 200, 40), SIDEWALK: (40, 40, 220)}  # BGR: 초록/빨강
_LABELS     = {ROAD: "ROAD (차도)", SIDEWALK: "SIDEWALK (인도)", UNKNOWN: "UNKNOWN"}

# ---------------------------------------------------------------------------
# Math helpers (YOLOv8-seg 디코딩)
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
    """Distributed focal loss decode: (N, 64) -> (N, 4)"""
    n = raw.shape[0]
    weights = np.arange(reg_max, dtype=np.float32)
    x = _softmax(raw.reshape(n, 4, reg_max))
    return (x * weights).sum(axis=-1)


def _dist2bbox(dist: np.ndarray, grid: np.ndarray) -> np.ndarray:
    return np.concatenate([grid - dist[:, :2], grid + dist[:, 2:]], axis=-1)


# ---------------------------------------------------------------------------
# Output layer 자동 감지 (YOLOv8-seg: bbox/cls/mask/proto 헤드)
# ---------------------------------------------------------------------------

class LayerAutoDetector:
    _STRIDES  = [8, 16, 32]
    _BBOX_CH  = 64
    _MASK_CH  = 32

    def detect(
        self,
        res: Dict[str, np.ndarray],
        input_h: int,
        input_w: int,
        num_classes: int,
    ) -> Tuple[Optional[str], List[Tuple[str, str, str, int]]]:
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
                _log.warning("stride=%d head 불완전: %s", stride, list(h))

        return proto_name, layers


# ---------------------------------------------------------------------------
# YOLOv8-seg 후처리 → 픽셀별 class_map / conf_map
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

    class_map = np.full((input_h, input_w), UNKNOWN, dtype=np.int32)
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

    proto_flat = proto.reshape(-1, 32)  # (proto_h*proto_w, 32)
    accum = np.zeros((num_classes, input_h, input_w), dtype=np.float32)

    for i in idxs:
        cls  = int(cls_ids[i])
        coef = coeffs[i]
        raw  = coef @ proto_flat.T                         # (proto_h*proto_w,)
        mask = _sigmoid(raw.reshape(proto_h, proto_w))
        mask_up = cv2.resize(mask, (input_w, input_h), interpolation=cv2.INTER_LINEAR)

        # BBox 클리핑: proto mask가 전체 이미지로 번지는 현상 방지
        bx1 = int(np.clip(bboxes[i][0], 0, input_w))
        by1 = int(np.clip(bboxes[i][1], 0, input_h))
        bx2 = int(np.clip(bboxes[i][2], 0, input_w))
        by2 = int(np.clip(bboxes[i][3], 0, input_h))
        clipped = np.zeros((input_h, input_w), dtype=np.float32)
        clipped[by1:by2, bx1:bx2] = mask_up[by1:by2, bx1:bx2]

        accum[cls] = np.maximum(accum[cls], clipped)

    valid = accum.max(axis=0) > conf_thr
    class_map[valid] = accum[:, valid].argmax(axis=0).astype(np.int32)
    conf_map[valid]  = accum[:, valid].max(axis=0)

    return class_map, conf_map


# ---------------------------------------------------------------------------
# ROI 픽셀 다수결 → (class_id, confidence)
# ---------------------------------------------------------------------------

def _classify_roi(
    class_map: np.ndarray,
    conf_map: np.ndarray,
    roi_x: Tuple[float, float],
    roi_y: Tuple[float, float],
    conf_thr: float,
) -> Tuple[int, float]:
    h, w = class_map.shape
    x1, x2 = int(w * roi_x[0]), int(w * roi_x[1])
    y1, y2 = int(h * roi_y[0]), int(h * roi_y[1])

    roi_cls  = class_map[y1:y2, x1:x2]
    roi_conf = conf_map[y1:y2, x1:x2]

    road_mask = (roi_cls == ROAD)     & (roi_conf > conf_thr)
    sw_mask   = (roi_cls == SIDEWALK) & (roi_conf > conf_thr)

    road_px = int(road_mask.sum())
    sw_px   = int(sw_mask.sum())

    if road_px == 0 and sw_px == 0:
        return UNKNOWN, 0.0
    if road_px > sw_px:
        return ROAD,     float(roi_conf[road_mask].mean())
    return SIDEWALK, float(roi_conf[sw_mask].mean())


# ---------------------------------------------------------------------------
# 결과 이미지 생성
# ---------------------------------------------------------------------------

def _draw_result(
    orig_frame: np.ndarray,
    class_map: np.ndarray,
    conf_map: np.ndarray,
    result_cls: int,
    result_conf: float,
    roi_x: Tuple[float, float],
    roi_y: Tuple[float, float],
    conf_thr: float,
    alpha: float = 0.45,
) -> np.ndarray:
    orig_h, orig_w = orig_frame.shape[:2]
    input_h, input_w = class_map.shape

    seg_overlay = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
    conf_up = cv2.resize(conf_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    for cls_id, color in _SEG_COLORS.items():
        cls_up = cv2.resize(
            (class_map == cls_id).astype(np.uint8),
            (orig_w, orig_h),
            interpolation=cv2.INTER_NEAREST,
        ).astype(bool)
        valid = cls_up & (conf_up > conf_thr)
        seg_overlay[valid] = color

    vis = cv2.addWeighted(orig_frame, 1.0, seg_overlay, alpha, 0)

    # ROI 박스 (노란색)
    rx1, rx2 = int(orig_w * roi_x[0]), int(orig_w * roi_x[1])
    ry1, ry2 = int(orig_h * roi_y[0]), int(orig_h * roi_y[1])
    cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 230, 230), 2)
    cv2.putText(vis, "ROI", (rx1 + 4, ry1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 230, 230), 2, cv2.LINE_AA)

    # 판별 결과 텍스트
    label = _LABELS.get(result_cls, "UNKNOWN")
    color = _SEG_COLORS.get(result_cls, (200, 200, 200))
    cv2.putText(vis, label, (20, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, color, 3, cv2.LINE_AA)
    cv2.putText(vis, f"conf: {result_conf:.3f}", (20, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)

    # 범례
    lx = orig_w - 160
    cv2.rectangle(vis, (lx, 15), (lx + 14, 30), _SEG_COLORS[ROAD], -1)
    cv2.putText(vis, "Road",     (lx + 18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1)
    cv2.rectangle(vis, (lx, 38), (lx + 14, 53), _SEG_COLORS[SIDEWALK], -1)
    cv2.putText(vis, "Sidewalk", (lx + 18, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1)

    return vis


# ---------------------------------------------------------------------------
# 단일 이미지 추론
# ---------------------------------------------------------------------------

def infer_image(
    pipeline,
    input_name: str,
    input_h: int,
    input_w: int,
    proto_name: str,
    layers: List[Tuple[str, str, str, int]],
    image_path: Path,
    conf_thr: float,
    nms_thr: float,
    roi_x: Tuple[float, float],
    roi_y: Tuple[float, float],
    out_dir: Path,
    show: bool,
    swap_classes: bool = False,
) -> Dict:
    frame = cv2.imread(str(image_path))
    if frame is None:
        _log.error("이미지 읽기 실패: %s", image_path)
        return {"file": str(image_path), "result": "ERROR"}

    img_rgb = cv2.cvtColor(
        cv2.resize(frame, (input_w, input_h)),
        cv2.COLOR_BGR2RGB,
    )
    input_tensor = np.expand_dims(img_rgb, axis=0).astype(np.uint8)

    res = pipeline.infer({input_name: input_tensor})

    class_map, conf_map = _postprocess(
        res, proto_name, layers, input_h, input_w, conf_thr, nms_thr, num_classes=2,
    )

    # 클래스 ID 스왑 (--swap-classes 시 0↔1 반전)
    if swap_classes:
        swapped = class_map.copy()
        swapped[class_map == ROAD]     = SIDEWALK
        swapped[class_map == SIDEWALK] = ROAD
        class_map = swapped

    # 진단: 전체 픽셀 클래스 분포 출력
    road_total = int((class_map == ROAD).sum())
    sw_total   = int((class_map == SIDEWALK).sum())
    unk_total  = int((class_map == UNKNOWN).sum())
    total_px   = input_h * input_w
    _log.info(
        "[%s] 픽셀분포 road=%d(%.1f%%)  sidewalk=%d(%.1f%%)  unknown=%d(%.1f%%)",
        image_path.name,
        road_total, road_total / total_px * 100,
        sw_total,   sw_total   / total_px * 100,
        unk_total,  unk_total  / total_px * 100,
    )

    result_cls, result_conf = _classify_roi(class_map, conf_map, roi_x, roi_y, conf_thr)

    # Fail-Safe: 감지 없으면 SIDEWALK
    if result_cls == UNKNOWN:
        result_cls  = SIDEWALK
        result_conf = 0.0

    label = _LABELS[result_cls]
    _log.info("[%s] -> %s  conf=%.3f", image_path.name, label, result_conf)

    vis = _draw_result(frame, class_map, conf_map, result_cls, result_conf,
                       roi_x, roi_y, conf_thr)

    out_path = out_dir / f"{image_path.stem}_seg{image_path.suffix}"
    cv2.imwrite(str(out_path), vis)
    _log.info("저장: %s", out_path)

    if show:
        cv2.imshow(f"{image_path.name} - 세그멘테이션 결과", vis)
        _log.info("창을 닫으려면 아무 키나 누르세요.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return {
        "file":       str(image_path),
        "result":     label,
        "confidence": round(result_conf, 4),
        "output":     str(out_path),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not _HAILO_OK:
        _log.error("hailo_platform 미설치. Raspberry Pi 5 + Hailo-8 SDK 환경에서 실행하세요.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Hailo-8 정적 이미지 도로/인도 세그멘테이션")
    parser.add_argument("images", nargs="+", type=Path,
                        help="추론할 이미지 파일 (JPG/PNG)")
    parser.add_argument("--hef", type=Path,
                        default=Path(__file__).parent / "best.hef",
                        help="HEF 모델 경로 (기본값: best.hef)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="결과 저장 폴더 (기본값: 원본 이미지와 동일 폴더)")
    parser.add_argument("--conf", type=float, default=0.40,
                        help="신뢰도 임계값 (기본값: 0.40)")
    parser.add_argument("--nms",  type=float, default=0.50,
                        help="NMS IoU 임계값 (기본값: 0.50)")
    parser.add_argument("--roi-x", type=float, nargs=2, default=[0.3, 0.7],
                        metavar=("X1_RATIO", "X2_RATIO"),
                        help="ROI 가로 범위 비율 (기본값: 0.3 0.7)")
    parser.add_argument("--roi-y", type=float, nargs=2, default=[0.6, 1.0],
                        metavar=("Y1_RATIO", "Y2_RATIO"),
                        help="ROI 세로 범위 비율 (기본값: 0.6 1.0)")
    parser.add_argument("--alpha", type=float, default=0.45,
                        help="세그멘테이션 오버레이 투명도 (기본값: 0.45)")
    parser.add_argument("--show", action="store_true",
                        help="각 이미지 처리 후 결과 창 표시")
    parser.add_argument("--swap-classes", action="store_true",
                        help="class 0↔1 반전 (모델 레이블이 반대일 때 사용)")
    args = parser.parse_args()

    if not args.hef.exists():
        _log.error("HEF 파일을 찾을 수 없음: %s", args.hef)
        sys.exit(1)

    valid_images = [p for p in args.images if p.exists()]
    if not valid_images:
        _log.error("유효한 이미지 파일 없음")
        sys.exit(1)

    _log.info("HEF 로드 중: %s", args.hef)
    hef = HEF(str(args.hef))
    info = hef.get_input_vstream_infos()[0]
    raw_shape = info.shape
    input_h, input_w = (
        (raw_shape[1], raw_shape[2]) if len(raw_shape) == 4
        else (raw_shape[0], raw_shape[1])
    )
    input_name = info.name
    _log.info("모델 입력: %dx%d  name=%s", input_w, input_h, input_name)

    roi_x = tuple(args.roi_x)
    roi_y = tuple(args.roi_y)

    results = []

    with VDevice() as target:
        params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        ng = target.configure(hef, params)[0]
        in_params  = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
        out_params = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

        with ng.activate(ng.create_params()):
            with InferVStreams(ng, in_params, out_params) as pipeline:

                # 레이어 자동 감지 (dummy run)
                _log.info("출력 레이어 자동 감지 중...")
                dummy = np.zeros((1, input_h, input_w, 3), dtype=np.uint8)
                dry   = pipeline.infer({input_name: dummy})

                detector = LayerAutoDetector()
                proto_name, layers = detector.detect(dry, input_h, input_w, num_classes=2)

                if proto_name is None or len(layers) == 0:
                    _log.error(
                        "레이어 감지 실패. 출력 텐서: %s",
                        [(k, v.shape) for k, v in dry.items()],
                    )
                    sys.exit(1)

                _log.info("Proto 레이어: %s", proto_name)
                for bn, cn, mn, s in layers:
                    _log.info("  stride=%-2d | bbox=%s  cls=%s  mask=%s", s, bn, cn, mn)

                for img_path in valid_images:
                    out_dir = args.out_dir if args.out_dir else img_path.parent
                    out_dir.mkdir(parents=True, exist_ok=True)

                    r = infer_image(
                        pipeline, input_name, input_h, input_w,
                        proto_name, layers,
                        img_path, args.conf, args.nms,
                        roi_x, roi_y, out_dir, args.show,
                        swap_classes=args.swap_classes,
                    )
                    results.append(r)

    print("\n===== 추론 결과 요약 =====")
    for r in results:
        print(f"  {Path(r['file']).name:30s}  {r['result']:25s}  conf={r.get('confidence', '-')}")
    print("==========================")


if __name__ == "__main__":
    main()
