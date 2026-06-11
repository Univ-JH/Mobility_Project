import numpy as np
import cv2
import os
from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                            InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)

# ==========================================
# 1. 환경 및 수학 함수 설정 (최적화 버전)
# ==========================================
HEF_PATH = "best.hef"
IMAGE_PATH = "img/screenshot1.png"
OUTPUT_PATH = "img/screenshot1_output.png"

# 클래스별 색상 (BGR 기준) - 0: 인도(초록), 1: 차도(빨강)
COLORS = {0: (0, 255, 0), 1: (0, 0, 255)} 

# 🛠️ [튜닝 핵심 포인트]
CONFIDENCE_THRESHOLD = 0.55  # 인식 확률 임계값 (결과가 너무 적으면 0.25로 낮추세요)
NMS_THRESHOLD = 0.3           # 중복 제거 임계값 (영역이 겹쳐서 나오면 수치를 낮추세요)

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
def run_segmentation():
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

        # 투명한 도화지 생성 (시각화용)
        overlay_canvas = np.zeros_like(img_resized, dtype=np.uint8)

        print("✅ 3. Hailo-8 NPU 추론 실행...")
        network_group_params = network_group.create_params()
        with network_group.activate(network_group_params):
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                res = infer_pipeline.infer({input_info.name: input_data})

        print("✅ 4. 고속 후처리 및 마스크 조립 진행 중...")
        
        # 접두사 파악
        prefix = list(res.keys())[0].split('/')[0]
        
        # 텐서 맵핑 (출력 형태 기반) stride: 8, 16, 32
        layers_info = [
            (f'{prefix}/conv44', f'{prefix}/conv45', f'{prefix}/conv46', 8),
            (f'{prefix}/conv60', f'{prefix}/conv61', f'{prefix}/conv62', 16),
            (f'{prefix}/conv73', f'{prefix}/conv74', f'{prefix}/conv75', 32),
        ]
        
        # 프로토타입 텐서 (전체 도화지) 추출
        proto_tensor = res[f'{prefix}/conv48'][0] # (160, 160, 32)
        
        all_bboxes, all_scores, all_class_ids, all_mask_coeffs = [], [], [], []

        for bbox_n, cls_n, mask_n, stride in layers_info:
            bbox_t, cls_t, mask_t = res[bbox_n][0], res[cls_n][0], res[mask_n][0]
            H, W = bbox_t.shape[:2]
            
            bbox_t = bbox_t.reshape(-1, 4, 16)
            cls_t = cls_t.reshape(-1, 2) # 인도, 차도 2개 클래스
            mask_t = mask_t.reshape(-1, 32)

            cls_scores = sigmoid(cls_t)
            max_scores = np.max(cls_scores, axis=-1)
            class_ids = np.argmax(cls_scores, axis=-1)

            # 임계값 필터링
            valid_idx = max_scores > CONFIDENCE_THRESHOLD
            if not np.any(valid_idx):
                continue

            valid_bbox = dfl(bbox_t[valid_idx])
            grid = make_grid(H, W, stride)[valid_idx]
            decoded_bbox = dist2bbox(valid_bbox, grid)

            all_bboxes.append(decoded_bbox)
            all_scores.append(max_scores[valid_idx])
            all_class_ids.append(class_ids[valid_idx])
            all_mask_coeffs.append(mask_t[valid_idx])

        # 유효 객체 존재 시 시각화
        if all_bboxes:
            all_bboxes = np.concatenate(all_bboxes, axis=0)
            all_scores = np.concatenate(all_scores, axis=0)
            all_class_ids = np.concatenate(all_class_ids, axis=0)
            all_mask_coeffs = np.concatenate(all_mask_coeffs, axis=0)

            # NMS : 중복 박스 제거
            boxes_xywh = [[b[0], b[1], b[2]-b[0], b[3]-b[1]] for b in all_bboxes]
            indices = cv2.dnn.NMSBoxes(boxes_xywh, all_scores.tolist(), CONFIDENCE_THRESHOLD, NMS_THRESHOLD)

            if len(indices) > 0:
                indices = np.array(indices).flatten()
                
                # 💡 [핵심 최적화] 클래스별로 최종 마스크를 통합 관리합니다.
                final_masks = np.zeros((2, input_height, input_width), dtype=np.float32)
                
                # NMS 통과한 객체들의 가중치를 프로토타입과 행렬 곱 연산
                for idx in indices:
                    idx = int(idx)
                    cls_id = all_class_ids[idx]
                    coeffs = all_mask_coeffs[idx] # (32,)

                    # 수학적 마스크 생성 (MatMul)
                    mask = coeffs @ proto_tensor.reshape(-1, 32).T          # (25600,)
                    mask = sigmoid(mask)                                    # 확률 변환
                    mask_resized = cv2.resize(mask.reshape(160, 160), (input_width, input_height))

                    # 해당 클래스 최종 마스크에 합산 (최대값 취함)
                    final_masks[cls_id] = np.maximum(final_masks[cls_id], mask_resized)

                # 💡 [비교/보정] 한 픽셀이 인도일 확률과 차도일 확률을 비교하여 최종 결정
                class_map = np.argmax(final_masks, axis=0) # (input_height, input_width)
                max_conf_map = np.max(final_masks, axis=0) # 해당 픽셀의 최대 확률값

                # 투명 도화지에 색칠하기
                for cls_id, color in COLORS.items():
                    # 해당 클래스로 판단되고, 확률이 임계값 이상인 픽셀만 색칠
                    canvas_condition = (class_map == cls_id) & (max_conf_map > CONFIDENCE_THRESHOLD)
                    overlay_canvas[canvas_condition] = color

            # 원본 이미지 크기로 복원 및 Alpha Blending 합성
            mask_orig = cv2.resize(overlay_canvas, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
            original_img = cv2.addWeighted(original_img, 1.0, mask_orig, 0.4, 0) # 원본100% + 마스크40%

        cv2.imwrite(OUTPUT_PATH, original_img)
        print(f"\n🎉 모든 과정 완료! 최적화된 결과 [{OUTPUT_PATH}] 파일을 확인하세요.")

if __name__ == "__main__":
    run_segmentation()