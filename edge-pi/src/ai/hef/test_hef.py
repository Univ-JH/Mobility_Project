import argparse
import numpy as np
import cv2
import time
import socket
from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                            InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)

# ==========================================
# 1. 설정 및 파라미터
# ==========================================
HEF_PATH = "best.hef"
CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.5

# 클래스 맵핑 (0: 차도/초록, 1: 인도/빨강)
ROAD_CLASS = 0
SIDEWALK_CLASS = 1
COLORS = {ROAD_CLASS: (0, 255, 0), SIDEWALK_CLASS: (0, 0, 255)} # BGR

# 관심 영역(ROI) 비율 설정: 바퀴 앞부분(화면 중앙 하단)
ROI_X_RATIO = (0.3, 0.7)
ROI_Y_RATIO = (0.6, 1.0)

# ==========================================
# 수학 함수들
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
# 2. 메인 실시간 추론 루프
# ==========================================
def run_realtime_inference(display=True):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    VISION_ADDR = ("127.0.0.1", 5005)
    cap = None

    print("✅ 1. HEF 로드 및 NPU 초기화 중...")
    hef = HEF(HEF_PATH)
    input_info = hef.get_input_vstream_infos()[0]
    input_shape = input_info.shape
    input_height, input_width = input_shape[1:3] if len(input_shape) == 4 else input_shape[0:2]

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다. 카메라 연결 및 설정을 확인하세요.")
        udp_sock.close()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("✅ 2. NPU 가속기 연결 중...")
    try:
        with VDevice() as target:
            configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_group = target.configure(hef, configure_params)[0]

            input_vstreams_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
            output_vstreams_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

            network_group_params = network_group.create_params()

            with network_group.activate(network_group_params):
                with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                    print("🚀 실시간 주행 상태 판별을 시작합니다! (종료하려면 'q' 입력)")

                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            print("프레임을 읽어오지 못했습니다.")
                            break

                        start_time = time.time()
                        orig_h, orig_w = frame.shape[:2]

                        # 1. 입력 이미지 전처리
                        img_resized = cv2.resize(frame, (input_width, input_height))
                        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
                        input_data = np.expand_dims(img_rgb, axis=0)

                        # 2. NPU 추론
                        res = infer_pipeline.infer({input_info.name: input_data})
                        prefix = list(res.keys())[0].split('/')[0]

                        # 3. 고속 후처리
                        layers_info = [
                            (f'{prefix}/conv44', f'{prefix}/conv45', f'{prefix}/conv46', 8),
                            (f'{prefix}/conv60', f'{prefix}/conv61', f'{prefix}/conv62', 16),
                            (f'{prefix}/conv73', f'{prefix}/conv74', f'{prefix}/conv75', 32),
                        ]
                        proto_tensor = res[f'{prefix}/conv48'][0]

                        all_bboxes, all_scores, all_class_ids, all_mask_coeffs = [], [], [], []

                        for bbox_n, cls_n, mask_n, stride in layers_info:
                            bbox_t, cls_t, mask_t = res[bbox_n][0], res[cls_n][0], res[mask_n][0]
                            H, W = bbox_t.shape[:2]

                            bbox_t = bbox_t.reshape(-1, 4, 16)
                            cls_t = cls_t.reshape(-1, 2)
                            mask_t = mask_t.reshape(-1, 32)

                            cls_scores = sigmoid(cls_t)
                            max_scores = np.max(cls_scores, axis=-1)
                            class_ids = np.argmax(cls_scores, axis=-1)

                            valid_idx = max_scores > CONFIDENCE_THRESHOLD
                            if not np.any(valid_idx):
                                continue

                            valid_bbox = dfl(bbox_t[valid_idx])
                            grid = make_grid(H, W, stride)[valid_idx]

                            all_bboxes.append(dist2bbox(valid_bbox, grid))
                            all_scores.append(max_scores[valid_idx])
                            all_class_ids.append(class_ids[valid_idx])
                            all_mask_coeffs.append(mask_t[valid_idx])

                        # 4. 마스크 조립 및 판별 로직
                        current_state = "UNKNOWN"
                        state_color = (255, 255, 255)

                        overlay_canvas = np.zeros_like(img_resized, dtype=np.uint8)

                        if all_bboxes:
                            all_bboxes = np.concatenate(all_bboxes, axis=0)
                            all_scores = np.concatenate(all_scores, axis=0)
                            all_class_ids = np.concatenate(all_class_ids, axis=0)
                            all_mask_coeffs = np.concatenate(all_mask_coeffs, axis=0)

                            boxes_xywh = [[b[0], b[1], b[2]-b[0], b[3]-b[1]] for b in all_bboxes]
                            indices = cv2.dnn.NMSBoxes(boxes_xywh, all_scores.tolist(), CONFIDENCE_THRESHOLD, NMS_THRESHOLD)

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
                                    canvas_condition = (class_map == cls_id) & (max_conf_map > CONFIDENCE_THRESHOLD)
                                    overlay_canvas[canvas_condition] = color

                                roi_x1 = int(input_width * ROI_X_RATIO[0])
                                roi_x2 = int(input_width * ROI_X_RATIO[1])
                                roi_y1 = int(input_height * ROI_Y_RATIO[0])
                                roi_y2 = int(input_height * ROI_Y_RATIO[1])

                                roi_class_map = class_map[roi_y1:roi_y2, roi_x1:roi_x2]
                                roi_conf_map = max_conf_map[roi_y1:roi_y2, roi_x1:roi_x2]

                                road_pixels = np.sum((roi_class_map == ROAD_CLASS) & (roi_conf_map > CONFIDENCE_THRESHOLD))
                                sidewalk_pixels = np.sum((roi_class_map == SIDEWALK_CLASS) & (roi_conf_map > CONFIDENCE_THRESHOLD))

                                if road_pixels == 0 and sidewalk_pixels == 0:
                                    current_state = "UNKNOWN"
                                elif road_pixels > sidewalk_pixels:
                                    current_state = "ROAD (차도)"
                                    state_color = (0, 255, 0)
                                    try:
                                        udp_sock.sendto(b"1", VISION_ADDR)
                                    except Exception as e:
                                        print(f"[WARN] UDP 송신 실패: {e}")
                                else:
                                    current_state = "SIDEWALK (인도) - WARNING!"
                                    state_color = (0, 0, 255)
                                    try:
                                        udp_sock.sendto(b"0", VISION_ADDR)
                                    except Exception as e:
                                        print(f"[WARN] UDP 송신 실패: {e}")

                        fps = 1.0 / (time.time() - start_time)
                        print(f"STATUS: {current_state} | FPS: {fps:.1f}")

                        if display:
                            # 5. 화면 표시 (알파 블렌딩)
                            mask_orig = cv2.resize(overlay_canvas, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
                            frame = cv2.addWeighted(frame, 1.0, mask_orig, 0.4, 0)

                            # 6. UI 그리기
                            draw_x1 = int(orig_w * ROI_X_RATIO[0])
                            draw_x2 = int(orig_w * ROI_X_RATIO[1])
                            draw_y1 = int(orig_h * ROI_Y_RATIO[0])
                            draw_y2 = int(orig_h * ROI_Y_RATIO[1])

                            cv2.rectangle(frame, (draw_x1, draw_y1), (draw_x2, draw_y2), (255, 255, 0), 2)
                            cv2.putText(frame, "Detection ROI", (draw_x1, draw_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                            cv2.putText(frame, f"STATUS: {current_state}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, state_color, 3)
                            cv2.putText(frame, f"FPS: {fps:.1f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                            cv2.imshow("Smart Mobility Dashboard", frame)

                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break
    finally:
        if cap is not None:
            cap.release()
        if display:
            cv2.destroyAllWindows()
        udp_sock.close()
        print("✅ 프로그램이 종료되었습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-display", action="store_true", help="화면 출력 비활성화 (headless 모드)")
    args = parser.parse_args()
    run_realtime_inference(display=not args.no_display)
