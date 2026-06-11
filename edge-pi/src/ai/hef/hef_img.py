import numpy as np
import cv2
import os
import argparse
from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                            InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)

# ==========================================
# 설정
# ==========================================
HEF_PATH = "best.hef"
DEFAULT_INPUT = "img/img (41).png"
OUTPUT_DIR = "imgtrans"

VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

# 클래스별 색상 (BGR 기준) - 0: 차도(빨강), 1: 인도(초록)
COLORS = {0: (0, 0, 255), 1: (0, 255, 0)}


# ==========================================
# 수학 유틸
# ==========================================
def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -50, 50)))

def softmax(x, axis=-1):
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / e_x.sum(axis=axis, keepdims=True)

def make_grid(h, w, stride):
    yv, xv = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    grid = np.stack((xv, yv), axis=-1) + 0.5
    return grid.reshape(-1, 2) * stride

def dfl(position, reg_max=16):
    x = softmax(position, axis=-1)
    weights = np.arange(reg_max, dtype=np.float32)
    return np.sum(x * weights, axis=-1)

def dist2bbox(distance, grid):
    x1y1 = grid - distance[:, :2]
    x2y2 = grid + distance[:, 2:]
    return np.concatenate((x1y1, x2y2), axis=-1)


# ==========================================
# 공통: 단일 프레임 추론 + 시각화
# ==========================================
def infer_frame(frame, infer_pipeline, input_info, input_height, input_width,
                prefix, layers_info, conf_threshold, nms_threshold):
    orig_h, orig_w = frame.shape[:2]
    img_resized = cv2.resize(frame, (input_width, input_height))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    input_data = np.expand_dims(img_rgb, axis=0)

    res = infer_pipeline.infer({input_info.name: input_data})

    overlay_canvas = np.zeros_like(img_resized, dtype=np.uint8)
    proto_tensor = res[f'{prefix}/conv48'][0]  # (160, 160, 32)

    all_bboxes, all_scores, all_class_ids, all_mask_coeffs = [], [], [], []

    for bbox_n, cls_n, mask_n, stride in layers_info:
        bbox_t, cls_t, mask_t = res[bbox_n][0], res[cls_n][0], res[mask_n][0]
        H, W = bbox_t.shape[:2]

        bbox_t = bbox_t.reshape(-1, 4, 16)
        cls_t = cls_t.reshape(-1, 2)  # 차도(0), 인도(1)
        mask_t = mask_t.reshape(-1, 32)

        cls_scores = sigmoid(cls_t)
        max_scores = np.max(cls_scores, axis=-1)
        class_ids = np.argmax(cls_scores, axis=-1)

        valid_idx = max_scores > conf_threshold
        if not np.any(valid_idx):
            continue

        valid_bbox = dfl(bbox_t[valid_idx])
        grid = make_grid(H, W, stride)[valid_idx]
        decoded_bbox = dist2bbox(valid_bbox, grid)

        all_bboxes.append(decoded_bbox)
        all_scores.append(max_scores[valid_idx])
        all_class_ids.append(class_ids[valid_idx])
        all_mask_coeffs.append(mask_t[valid_idx])

    if all_bboxes:
        all_bboxes = np.concatenate(all_bboxes, axis=0)
        all_scores = np.concatenate(all_scores, axis=0)
        all_class_ids = np.concatenate(all_class_ids, axis=0)
        all_mask_coeffs = np.concatenate(all_mask_coeffs, axis=0)

        boxes_xywh = [[b[0], b[1], b[2]-b[0], b[3]-b[1]] for b in all_bboxes]
        indices = cv2.dnn.NMSBoxes(boxes_xywh, all_scores.tolist(), conf_threshold, nms_threshold)

        if len(indices) > 0:
            indices = np.array(indices).flatten()
            final_masks = np.zeros((2, input_height, input_width), dtype=np.float32)

            for idx in indices:
                idx = int(idx)
                cls_id = all_class_ids[idx]
                coeffs = all_mask_coeffs[idx]

                mask = coeffs @ proto_tensor.reshape(-1, 32).T
                mask = sigmoid(mask)
                mask_resized = cv2.resize(mask.reshape(160, 160), (input_width, input_height))
                final_masks[cls_id] = np.maximum(final_masks[cls_id], mask_resized)

            class_map = np.argmax(final_masks, axis=0)
            max_conf_map = np.max(final_masks, axis=0)

            for cls_id, color in COLORS.items():
                canvas_condition = (class_map == cls_id) & (max_conf_map > conf_threshold)
                overlay_canvas[canvas_condition] = color

        mask_orig = cv2.resize(overlay_canvas, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        frame = cv2.addWeighted(frame, 1.0, mask_orig, 0.4, 0)

    return frame


# ==========================================
# NPU 초기화 공통
# ==========================================
def init_npu(hef):
    input_info = hef.get_input_vstream_infos()[0]
    input_shape = input_info.shape
    input_height, input_width = input_shape[1:3] if len(input_shape) == 4 else input_shape[0:2]
    return input_info, input_height, input_width


def build_layers_info(prefix):
    return [
        (f'{prefix}/conv44', f'{prefix}/conv45', f'{prefix}/conv46', 8),
        (f'{prefix}/conv60', f'{prefix}/conv61', f'{prefix}/conv62', 16),
        (f'{prefix}/conv73', f'{prefix}/conv74', f'{prefix}/conv75', 32),
    ]


# ==========================================
# 이미지 추론
# ==========================================
def run_image(input_path, conf_threshold, nms_threshold):
    print(f"🛠️  CONFIDENCE_THRESHOLD={conf_threshold}, NMS_THRESHOLD={nms_threshold}")
    print("✅ 1. HEF 파일 로드 및 NPU 초기화...")
    hef = HEF(HEF_PATH)
    input_info, input_height, input_width = init_npu(hef)

    frame = cv2.imread(input_path)
    if frame is None:
        raise FileNotFoundError(f"이미지를 열 수 없습니다: {os.path.abspath(input_path)}")

    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]
        input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

        print("✅ 2. Hailo-8 NPU 추론 실행...")
        network_group_params = network_group.create_params()
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as pipeline:
                # prefix 파악을 위해 더미 추론 1회
                dummy = np.expand_dims(
                    cv2.cvtColor(cv2.resize(frame, (input_width, input_height)), cv2.COLOR_BGR2RGB), axis=0
                )
                res0 = pipeline.infer({input_info.name: dummy})
                prefix = list(res0.keys())[0].split('/')[0]
                layers_info = build_layers_info(prefix)

                result = infer_frame(frame, pipeline, input_info, input_height, input_width,
                                     prefix, layers_info, conf_threshold, nms_threshold)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(OUTPUT_DIR, f"{name}_conf{conf_threshold}_nms{nms_threshold}{ext}")
    cv2.imwrite(output_path, result)
    print(f"\n🎉 완료! [{output_path}]")


# ==========================================
# 영상 추론
# ==========================================
def run_video(input_path, conf_threshold, nms_threshold):
    print(f"🛠️  CONFIDENCE_THRESHOLD={conf_threshold}, NMS_THRESHOLD={nms_threshold}")
    print("✅ 1. HEF 파일 로드 및 NPU 초기화...")
    hef = HEF(HEF_PATH)
    input_info, input_height, input_width = init_npu(hef)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {os.path.abspath(input_path)}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(input_path))
    output_path = os.path.join(OUTPUT_DIR, f"{name}_conf{conf_threshold}_nms{nms_threshold}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (orig_w, orig_h))

    print(f"✅ 2. 영상 추론 시작 (총 {total}프레임, {fps:.1f}fps)...")

    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]
        input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

        network_group_params = network_group.create_params()
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as pipeline:
                prefix = None
                layers_info = None
                frame_idx = 0

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # 첫 프레임에서 prefix 확정
                    if prefix is None:
                        dummy = np.expand_dims(
                            cv2.cvtColor(cv2.resize(frame, (input_width, input_height)), cv2.COLOR_BGR2RGB), axis=0
                        )
                        res0 = pipeline.infer({input_info.name: dummy})
                        prefix = list(res0.keys())[0].split('/')[0]
                        layers_info = build_layers_info(prefix)

                    result = infer_frame(frame, pipeline, input_info, input_height, input_width,
                                        prefix, layers_info, conf_threshold, nms_threshold)
                    writer.write(result)

                    frame_idx += 1
                    if frame_idx % 30 == 0:
                        pct = frame_idx / total * 100 if total > 0 else 0
                        print(f"   {frame_idx}/{total} 프레임 ({pct:.1f}%)")

    cap.release()
    writer.release()
    print(f"\n🎉 완료! [{output_path}]")


# ==========================================
# 진입점
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hailo-8 YOLOv8-seg 추론 (이미지/영상)")
    parser.add_argument(
        "input", nargs="?", default=DEFAULT_INPUT,
        help=f"입력 파일 경로 — 이미지 또는 영상 (기본값: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--conf", type=float, default=0.55,
        help="신뢰도 임계값 (기본값: 0.55)"
    )
    parser.add_argument(
        "--nms", type=float, default=0.3,
        help="NMS 임계값 (기본값: 0.3)"
    )
    args = parser.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    if ext in VIDEO_EXTS:
        run_video(args.input, args.conf, args.nms)
    else:
        run_image(args.input, args.conf, args.nms)
