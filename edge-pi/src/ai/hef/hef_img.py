import numpy as np
import cv2
import os
import argparse
from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                            InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)

# ==========================================
# 1. 환경 및 수학 함수 설정 (최적화 버전)
# ==========================================
HEF_PATH = "best.hef"
IMAGE_PATH = "img/img (41).png"
OUTPUT_DIR = "imgtrans"

# 클래스별 색상 (BGR 기준) - 0: 차도(빨강), 1: 인도(초록)
COLORS = {0: (0, 0, 255), 1: (0, 255, 0)}

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
    """ Bounding Box 디코딩 """
    x = softmax(position, axis=-1)
    weights = np.arange(reg_max, dtype=np.float32)
    return np.sum(x * weights, axis=-1)

def dist2bbox(distance, grid):
    """ 좌표 변환 """
    x1y1 = grid - distance[:, :2]
    x2y2 = grid + distance[:, 2:]
    return np.concatenate((x1y1, x2y2), axis=-1)

# ==========================================
# 메인 추론 및 시각화 로직
# ==========================================
def run_segmentation(conf_threshold, nms_threshold):
    print(f"🛠️  CONFIDENCE_THRESHOLD={conf_threshold}, NMS_THRESHOLD={nms_threshold}")
    print("✅ 1. HEF 파일 로드 및 NPU 초기화...")
    hef = HEF(HEF_PATH)
    input_info = hef.get_input_vstream_infos()[0]
    input_shape = input_info.shape
    input_height, input_width = input_shape[1:3] if len(input_shape) == 4 else input_shape[0:2]

    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]

        input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

        print("✅ 2. 입력 이미지 전처리 중...")
        original_img = cv2.imread(IMAGE_PATH)
        orig_h, orig_w = original_img.shape[:2]
        img_resized = cv2.resize(original_img, (input_width, input_height))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        input_data = np.expand_dims(img_rgb, axis=0)

        overlay_canvas = np.zeros_like(img_resized, dtype=np.uint8)

        print("✅ 3. Hailo-8 NPU 추론 실행...")
        network_group_params = network_group.create_params()
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                res = infer_pipeline.infer({input_info.name: input_data})

        print("✅ 4. 고속 후처리 및 마스크 조립 진행 중...")

        prefix = list(res.keys())[0].split('/')[0]

        layers_info = [
            (f'{prefix}/conv44', f'{prefix}/conv45', f'{prefix}/conv46', 8),
            (f'{prefix}/conv60', f'{prefix}/conv61', f'{prefix}/conv62', 16),
            (f'{prefix}/conv73', f'{prefix}/conv74', f'{prefix}/conv75', 32),
        ]

        proto_tensor = res[f'{prefix}/conv48'][0]  # (160, 160, 32)

        all_bboxes, all_scores, all_class_ids, all_mask_coeffs = [], [], [], []

        for bbox_n, cls_n, mask_n, stride in layers_info:
            bbox_t, cls_t, mask_t = res[bbox_n][0], res[cls_n][0], res[mask_n][0]
            H, W = bbox_t.shape[:2]

            bbox_t = bbox_t.reshape(-1, 4, 16)
            cls_t = cls_t.reshape(-1, 2)  # 차도(0), 인도(1) 2개 클래스
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
                    coeffs = all_mask_coeffs[idx]  # (32,)

                    mask = coeffs @ proto_tensor.reshape(-1, 32).T          # (25600,)
                    mask = sigmoid(mask)
                    mask_resized = cv2.resize(mask.reshape(160, 160), (input_width, input_height))

                    final_masks[cls_id] = np.maximum(final_masks[cls_id], mask_resized)

                class_map = np.argmax(final_masks, axis=0)
                max_conf_map = np.max(final_masks, axis=0)

                for cls_id, color in COLORS.items():
                    canvas_condition = (class_map == cls_id) & (max_conf_map > conf_threshold)
                    overlay_canvas[canvas_condition] = color

            mask_orig = cv2.resize(overlay_canvas, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            original_img = cv2.addWeighted(original_img, 1.0, mask_orig, 0.4, 0)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        base_name = os.path.basename(IMAGE_PATH)
        name, ext = os.path.splitext(base_name)
        output_path = os.path.join(OUTPUT_DIR, f"{name}_conf{conf_threshold}_nms{nms_threshold}{ext}")

        cv2.imwrite(output_path, original_img)
        print(f"\n🎉 모든 과정 완료! 결과 [{output_path}] 파일을 확인하세요.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hailo-8 YOLOv8-seg 추론")
    parser.add_argument(
        "--conf", type=float, default=0.55,
        help="신뢰도 임계값 (기본값: 0.55, 결과 부족시 0.25로 낮추세요)"
    )
    parser.add_argument(
        "--nms", type=float, default=0.3,
        help="NMS 임계값 (기본값: 0.3, 박스 겹침 심하면 낮추세요)"
    )
    args = parser.parse_args()
    run_segmentation(args.conf, args.nms)
