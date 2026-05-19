import os
import cv2
import time
import threading
import numpy as np
from collections import deque

try:
    from hailo_platform import (
        HEF, VDevice, HailoStreamInterface, InferVStreams, 
        ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType
    )
except ImportError:
    print("ERROR: hailo_platform 패키지가 설치되어 있지 않습니다. 라즈베리파이 로컬 환경에 HailoRT를 설치해주세요.")
    exit(1)

class CameraThread:
    """
    카메라 프레임을 별도 스레드에서 읽어오는 클래스.
    """
    def __init__(self, pipeline_str):
        self.cap = cv2.VideoCapture(pipeline_str, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("카메라를 초기화할 수 없습니다. libcamerasrc 파이프라인 및 장치 연결 상태를 확인하세요.")
        
        self.frame_queue = deque(maxlen=1)
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.frame_queue.append(frame)
            else:
                print("[FAULT] 카메라 프레임 수신 실패. 시야 불확실(Uncertain) 상태!")
                time.sleep(0.5)

    def get_frame(self):
        if len(self.frame_queue) > 0:
            return self.frame_queue[-1]
        return None

    def stop(self):
        self.running = False
        self.thread.join(timeout=2.0)
        self.cap.release()


def main():
    hef_path = 'best.hef'
    
    if not os.path.exists(hef_path):
        print(f"ERROR: 학습된 모델 파일({hef_path})을 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    gstreamer_pipeline = (
        "libcamerasrc ! "
        "video/x-raw, width=640, height=480, format=RGBx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=true max-buffers=1"
    )

    print("=== 이동장치 안전 비전 AI 데모 시작 ===")
    try:
        cam_thread = CameraThread(gstreamer_pipeline)
    except Exception as e:
        print(f"[FAULT] 시스템 초기화 실패: {e}")
        return

    print("Hailo-8 장치 및 HEF 로드 중...")
    try:
        hef = HEF(hef_path)
        
        with VDevice() as target:
            configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_groups = target.configure(hef, configure_params)
            network_group = network_groups[0]
            
            input_vstream_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
            output_vstream_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

            input_info = hef.get_input_vstream_infos()[0]
            input_shape = input_info.shape 
            
            if len(input_shape) == 4:
                model_h, model_w = input_shape[1], input_shape[2]
            else:
                model_h, model_w = input_shape[0], input_shape[1]
            
            print(f"추론 파이프라인 시작 완료! (모델 요구 입력 크기: {model_w}x{model_h})")
            print("종료하려면 화면을 선택하고 'q' 키를 누르세요.\n")

            # 클래스 이름 정의 및 직관적인 색상 지정
            # (기본값: 0=Street, 1=Sidewalk / 실행 후 색상이 거꾸로 매핑되어 있다면 0과 1의 텍스트를 서로 바꾸세요!)
            LABEL_MAP = {0: "Street", 1: "Sidewalk"}
            COLOR_MAP = {
                0: (255, 100, 0),   # Street: 든든한 파란색 계열 (BGR)
                1: (0, 0, 255)      # Sidewalk: 경고를 뜻하는 빨간색 계열 (BGR)
            }

            with network_group.activate():
                with InferVStreams(network_group, input_vstream_params, output_vstream_params) as infer_pipeline:
                    while True:
                        frame = cam_thread.get_frame()
                        if frame is None:
                            time.sleep(0.01)
                            continue
                        
                        display_frame = frame.copy()

                        # --- [1] Preprocessing ---
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        resized_frame = cv2.resize(frame_rgb, (model_w, model_h))
                        input_data = {input_info.name: np.expand_dims(resized_frame, axis=0)}

                        # --- [2] Inference ---
                        start_time = time.time()
                        infer_results = infer_pipeline.infer(input_data)
                        infer_time = (time.time() - start_time) * 1000

                        # --- [3] Postprocessing 및 영상 시각화 ---
                        h, w = display_frame.shape[:2]

                        for out_name, out_data in infer_results.items():
                            
                            # Case A: 바운딩 박스 모델인 경우 ([Batch, Boxes, 6])
                            if len(out_data.shape) == 3 and out_data.shape[2] == 6:
                                boxes = out_data[0]
                                for box in boxes:
                                    conf = box[4]
                                    if conf > 0.4:  # 신뢰도 임계값
                                        ymin, xmin, ymax, xmax = box[0], box[1], box[2], box[3]
                                        cls_id = int(box[5])
                                        
                                        label = LABEL_MAP.get(cls_id, f"Class {cls_id}")
                                        color = COLOR_MAP.get(cls_id, (0, 255, 0))
                                        
                                        # 좌표 복원 및 드로잉
                                        x1, y1 = int(xmin * w), int(ymin * h)
                                        x2, y2 = int(xmax * w), int(ymax * h)
                                        
                                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
                                        cv2.putText(display_frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
                                        
                            # Case B: 세그멘테이션 색칠형 모델인 경우 ([Batch, H, W, Class_Num])
                            elif len(out_data.shape) >= 3 and out_data.shape[-1] <= 5: 
                                # 각 픽셀별 가장 높은 점수를 가진 클래스 채널 추출
                                seg_map = np.argmax(out_data[0], axis=-1).astype(np.uint8)
                                seg_map_resized = cv2.resize(seg_map, (w, h), interpolation=cv2.INTER_NEAREST)
                                
                                # 반투명 색상을 입힐 도화지(Mask) 레이어 생성
                                mask = np.zeros_like(display_frame)
                                mask[seg_map_resized == 0] = COLOR_MAP[0] # Street 영역 채우기
                                mask[seg_map_resized == 1] = COLOR_MAP[1] # Sidewalk 영역 채우기
                                
                                # 원본 이미지에 마스크 이미지를 7:3 비율로 합성해 투명 오버레이 처리
                                display_frame = cv2.addWeighted(display_frame, 0.7, mask, 0.3, 0)
                                
                                # 시각적인 이해를 돕기 위한 색상 정보(Legend) 상단 표기
                                cv2.putText(display_frame, "[BLUE]: Street", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MAP[0], 2)
                                cv2.putText(display_frame, "[RED]: Sidewalk", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MAP[1], 2)

                        # 상태창 표기 (FPS 및 Latency)
                        fps_text = f"Latency: {infer_time:.1f}ms | FPS: {1000/infer_time:.1f}"
                        cv2.putText(display_frame, fps_text, (20, 40),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

                        # --- [4] 모니터 화면 출력 ---
                        cv2.imshow("Hailo Street/Sidewalk Detection", display_frame)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            print("사용자가 'q'를 눌러 종료합니다.")
                            break

    except KeyboardInterrupt:
        print("\n데모를 종료합니다.")
    except Exception as e:
        print(f"\n[FAULT] 구동 중 오류 발생: {e}")
    finally:
        print("자원 해제 중...")
        cam_thread.stop()
        cv2.destroyAllWindows()
        print("프로세스 종료 완료.")

if __name__ == "__main__":
    main()