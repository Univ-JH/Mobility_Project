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
    메인 스레드의 추론(Inference) 속도 저하로 인해 카메라 버퍼가 밀리는 현상(Latency)을 방지합니다.
    (AGENTS.md: 실시간성 보장을 위한 deque 스레드 큐 관리 규정 준수)
    """
    def __init__(self, pipeline_str):
        self.cap = cv2.VideoCapture(pipeline_str, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("카메라를 초기화할 수 없습니다. libcamerasrc 파이프라인 및 장치 연결 상태를 확인하세요.")
        
        self.frame_queue = deque(maxlen=1) # 가장 최신 프레임 1개만 유지
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.frame_queue.append(frame)
            else:
                # 카메라 읽기 실패 시 안전(Fail-Safe) 로그 출력
                print("[FAULT] 카메라 프레임 수신 실패. 시야 불확실(Uncertain) 상태! 보수 모드(감속/정지) 전환 필요.")
                time.sleep(0.5) # 에러 시 루프 폭주 방지

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
    
    # 잠재적 오류 방지 1: 모델 파일 존재 여부 검사
    if not os.path.exists(hef_path):
        print(f"ERROR: 학습된 모델 파일({hef_path})을 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    # 라즈베리파이 5 + 카메라 모듈 3 전용 GStreamer 파이프라인
    # libcamera를 사용하며, OpenCV 처리를 위해 RGBx를 BGR로 안전하게 변환
    gstreamer_pipeline = (
        "libcamerasrc ! "
        "video/x-raw, width=640, height=480, format=RGBx ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=true max-buffers=1"
    )

    print("=== 이동장치 안전 비전 AI 데모 시작 ===")
    print("카메라 및 캡처 스레드 초기화 중...")
    try:
        cam_thread = CameraThread(gstreamer_pipeline)
    except Exception as e:
        print(f"[FAULT] 시스템 초기화 실패: {e}. 하드웨어 보수 모드 전환.")
        return

    print("Hailo-8 장치 및 HEF 로드 중...")
    try:
        hef = HEF(hef_path)
        
        # VDevice 컨텍스트 매니저를 통해 NPU 장치 안전 할당 및 해제 보장
        with VDevice() as target:
            configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_groups = target.configure(hef, configure_params)
            network_group = network_groups[0]
            
            # 입력 데이터 포맷 지정 (OpenCV에서 변환된 UINT8 사용)
            input_vstream_params = InputVStreamParams.make(network_group, format_type=FormatType.UINT8)
            output_vstream_params = OutputVStreamParams.make(network_group, format_type=FormatType.FLOAT32)

            # 잠재적 오류 방지 2: 모델의 입력 형태(Shape)를 동적으로 파악 (하드코딩 방지)
            input_info = hef.get_input_vstream_infos()[0]
            input_shape = input_info.shape 
            
            # 버전에 따라 shape이 3차원(H,W,C) 또는 4차원(B,H,W,C)일 수 있음
            if len(input_shape) == 4:
                model_h, model_w = input_shape[1], input_shape[2]
            else:
                model_h, model_w = input_shape[0], input_shape[1]
            
            print(f"추론 파이프라인 시작 완료! (모델 요구 입력 크기: {model_w}x{model_h})")
            print("종료하려면 Ctrl+C를 누르세요.\n")

            with InferVStreams(network_group, input_vstream_params, output_vstream_params) as infer_pipeline:
                while True:
                    frame = cam_thread.get_frame()
                    if frame is None:
                        time.sleep(0.01)
                        continue

                    # --- [1] Preprocessing ---
                    # OpenCV BGR을 모델이 예상하는 RGB로 변환 후 리사이즈
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    resized_frame = cv2.resize(frame_rgb, (model_w, model_h))
                    
                    # Hailo 추론을 위해 Batch 차원(1)을 맨 앞에 추가
                    input_data = {input_info.name: np.expand_dims(resized_frame, axis=0)}

                    # --- [2] Inference ---
                    start_time = time.time()
                    infer_results = infer_pipeline.infer(input_data)
                    infer_time = (time.time() - start_time) * 1000

                    # --- [3] Postprocessing (최소 로깅) ---
                    print(f"[\u2714 추론 성공] 소요 시간: {infer_time:.2f}ms")
                    
                    # 모델에 따라 출력 텐서 갯수가 다름 (YOLO의 경우 클래스/박스 여러 개)
                    for out_name, out_data in infer_results.items():
                        # 주의: 여기서 NMS 및 박스 디코딩 처리를 추가하면 실제 좌표를 얻을 수 있습니다.
                        print(f"  - 출력 텐서명 '{out_name}' 데이터 형태: {out_data.shape}")
                    
                    print("-" * 40)
                    time.sleep(0.1) # 테스트 로그 과부하 방지 (실운영 시에는 제거/조절)

    except KeyboardInterrupt:
        print("\n사용자 요청에 의해 데모를 종료합니다.")
    except Exception as e:
        print(f"\n[FAULT] 추론 혹은 장치 제어 중 치명적 오류 발생: {e}")
        print("보수 모드 유지: 하드웨어 브레이크 서보 잠금 지시 전송 대기.")
    finally:
        print("카메라 자원 및 스레드 해제 중...")
        cam_thread.stop()
        print("프로세스 종료 완료.")

if __name__ == "__main__":
    main()
