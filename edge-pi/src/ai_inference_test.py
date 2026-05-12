import cv2
import numpy as np
import time
import json
from collections import deque
import os

# HailoRT 라이브러리 임포트 시도 (로컬 테스트 시 오류 방지용)
try:
    from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                                InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)
    HAILO_AVAILABLE = True
except ImportError:
    print("[경고] hailo_platform 모듈을 찾을 수 없습니다. (Mock 추론 모드로 작동합니다)")
    HAILO_AVAILABLE = False

class AIInferenceTest:
    def __init__(self, hef_path, config_path):
        # 하드웨어 캘리브레이션 분리 원칙 준수
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.width = self.config['camera']['width']
        self.height = self.config['camera']['height']
        self.fps = self.config['camera']['fps']
        
        # 안전 원칙: 시간 윈도우 다수결 안정화 (Fail-Safe)
        self.window_size = self.config['ai']['window_size_frames']
        self.threshold = self.config['ai']['threshold']
        self.history_window = deque(maxlen=self.window_size)
        
        self.hef_path = hef_path
        self.target = None
        self.infer_pipeline = None
        
        if HAILO_AVAILABLE:
            if not os.path.exists(self.hef_path):
                print(f"[오류] 모델 파일({self.hef_path})을 찾을 수 없습니다.")
                HAILO_AVAILABLE = False
            else:
                self._init_hailo()

    def _init_hailo(self):
        print(f"[Hailo] NPU 초기화 및 HEF 로드: {self.hef_path}")
        self.hef = HEF(self.hef_path)
        self.target = VDevice()
        
        # PCIe 인터페이스 NPU 설정
        configure_params = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        network_groups = self.target.configure(self.hef, configure_params)
        self.network_group = network_groups[0]
        
        # VStream (비디오 스트림) 입출력 파라미터 생성
        input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.UINT8)
        
        self.infer_pipeline = InferVStreams(self.network_group, input_vstreams_params, output_vstreams_params)
        
        # 모델의 입력 해상도 추출 (예: [1, 224, 224, 3])
        input_stream_info = self.hef.get_input_vstream_infos()[0]
        self.input_shape = input_stream_info.shape
        print(f"[Hailo] 기대 입력 Shape: {self.input_shape}")

    def capture_and_infer(self):
        # Camera Module 3 GStreamer 파이프라인 (libcamera 기반)
        # Low Latency 원칙을 위해 appsink까지의 버퍼를 최소화합니다.
        pipeline = (
            f"libcamerasrc ! video/x-raw, width={self.width}, height={self.height}, framerate={self.fps}/1 "
            f"! videoconvert ! appsink drop=true max-buffers=1"
        )
        print(f"[Camera] GStreamer 파이프라인 시작:\n {pipeline}")
        
        # Mock 테스트 시 카메라가 없는 환경일 수 있으므로 실패 처리를 유연하게 합니다.
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        if not cap.isOpened():
            print("[오류] Camera Module 3을 열 수 없습니다. 파이프라인 또는 권한을 확인하세요.")
            # 일반 웹캠으로 폴백 (디버깅용)
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return

        print("추론 루프 시작... (종료하려면 'q' 키를 누르세요)")
        
        # Hailo 추론 컨텍스트 진입
        if HAILO_AVAILABLE and self.infer_pipeline:
            with self.infer_pipeline:
                self._run_loop(cap)
        else:
            self._run_loop(cap)

        cap.release()
        cv2.destroyAllWindows()

    def _run_loop(self, cap):
        last_frame_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[경고] 프레임을 가져올 수 없습니다. 안전 모드(Fail-Safe)로 전환합니다.")
                self._handle_fail_safe()
                break
                
            # 카메라 렌즈 가림 방지 (너무 어두운지 검사 등 간단한 Fail-Safe)
            if np.mean(frame) < 10:
                self.history_window.append(1) # 위험으로 간주 (보이지 않으면 멈춘다)

            # 1. 전처리 (Resize 및 RGB 변환)
            input_data = self._preprocess(frame)
            
            # 2. AI 추론
            if HAILO_AVAILABLE and self.infer_pipeline:
                # Hailo 추론 API 호출 (Dict 형태)
                infer_results = self.infer_pipeline.infer(input_data)
                prediction = self._postprocess(infer_results)
            else:
                # NPU가 없는 경우 Mock 데이터 생성 (0: 차도, 1: 인도)
                prediction = np.random.choice([0, 1], p=[0.9, 0.1])
            
            # 3. 시간 윈도우 다수결 안정화 (Time-Window Stabilization)
            self.history_window.append(prediction)
            final_status = self._get_stabilized_status()
            
            # 4. 결과 시각화
            current_time = time.time()
            fps_text = f"FPS: {1.0 / (current_time - last_frame_time):.1f}"
            last_frame_time = current_time
            
            self._draw_overlay(frame, prediction, final_status, fps_text)
            cv2.imshow("Hailo-8 & Cam 3 Edge Inference Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def _preprocess(self, frame):
        # BGR -> RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if HAILO_AVAILABLE:
            h, w = self.input_shape[1:3]
            frame_resized = cv2.resize(frame_rgb, (w, h))
            
            # NPU 입력 규격에 맞게 차원 확장 (1, H, W, C)
            input_data = np.expand_dims(frame_resized, axis=0) 
            
            # 모델의 Input Layer 이름 추출
            input_name = self.hef.get_input_vstream_infos()[0].name
            return {input_name: input_data}
        return frame_rgb

    def _postprocess(self, infer_results):
        # NPU 결과 텐서에서 argmax 추출
        output_name = self.hef.get_output_vstream_infos()[0].name
        logits = infer_results[output_name]
        
        # Batch 0의 결과를 반환
        return int(np.argmax(logits[0]))

    def _get_stabilized_status(self):
        # 다수결 판정: 지정된 프레임 수 동안 위험(1)의 비율이 임계치를 넘는지 검사
        if len(self.history_window) == 0:
            return "UNCERTAIN"
            
        danger_count = sum(1 for p in self.history_window if p == 1)
        danger_ratio = danger_count / len(self.history_window)
        
        if danger_ratio >= self.threshold:
            return "DANGER (SIDEWALK)"
        else:
            return "SAFE (ROAD)"

    def _handle_fail_safe(self):
        print(">>> FAIL-SAFE TRIGGERED: 불확실성 감지. 서보모터 감속 신호 전송 로직이 실행되어야 합니다.")

    def _draw_overlay(self, frame, raw_pred, final_status, fps_text):
        color = (0, 255, 0) if "SAFE" in final_status else (0, 0, 255)
        raw_text = f"Raw Pred: {'Sidewalk' if raw_pred == 1 else 'Road'}"
        
        # 텍스트 오버레이
        cv2.putText(frame, raw_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(frame, final_status, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        cv2.putText(frame, fps_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

if __name__ == "__main__":
    # 실행 경로 설정
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    hef_model_path = os.path.join(BASE_DIR, "..", "models", "sidewalk_classifier.hef")
    config_file_path = os.path.join(BASE_DIR, "..", "config", "calibration.json")
    
    # 모델 디렉토리 생성 (오류 방지)
    os.makedirs(os.path.dirname(hef_model_path), exist_ok=True)
    
    test_app = AIInferenceTest(hef_path=hef_model_path, config_path=config_file_path)
    test_app.capture_and_infer()
