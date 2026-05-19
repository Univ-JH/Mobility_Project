import cv2
import numpy as np
import time
import json
import os
from collections import deque

# HailoRT 라이브러리 임포트 시도 (NPU 하드웨어 의존성)
try:
    from hailo_platform import (HEF, VDevice, HailoStreamInterface, ConfigureParams,
                                InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams)
    HAILO_AVAILABLE = True
except ImportError:
    print("[경고] hailo_platform 모듈을 찾을 수 없습니다. (Mock 추론 모드로 작동합니다)")
    HAILO_AVAILABLE = False

class ObjectDetectionDemo:
    def __init__(self, hef_path, config_path):
        # 1. 캘리브레이션 및 설정값 로드 (하드코딩 지양)
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.width = self.config['camera']['width']
        self.height = self.config['camera']['height']
        self.fps = self.config['camera']['fps']
        
        # 2. Hailo 설정 초기화
        self.hef_path = hef_path
        self.infer_pipeline = None
        
        if HAILO_AVAILABLE:
            if not os.path.exists(self.hef_path):
                print(f"[오류] 모델 파일({self.hef_path})을 찾을 수 없습니다. (경로 확인 필요)")
                global HAILO_AVAILABLE
                HAILO_AVAILABLE = False
            else:
                self._init_hailo()

    def _init_hailo(self):
        print(f"[Hailo] NPU 초기화 및 객체 탐지 HEF 로드: {self.hef_path}")
        self.hef = HEF(self.hef_path)
        self.target = VDevice()
        
        # PCIe 인터페이스 설정 (Hailo-8 M.2/PCIe)
        configure_params = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        network_groups = self.target.configure(self.hef, configure_params)
        self.network_group = network_groups[0]
        
        # 입출력 VStream 파라미터 (UINT8)
        input_vstreams_params = InputVStreamParams.make(self.network_group, format_type=FormatType.UINT8)
        output_vstreams_params = OutputVStreamParams.make(self.network_group, format_type=FormatType.FLOAT32)
        
        self.infer_pipeline = InferVStreams(self.network_group, input_vstreams_params, output_vstreams_params)
        
        # 모델 입력 형상 정보 가져오기 (예: [1, 640, 640, 3] for YOLO)
        input_stream_info = self.hef.get_input_vstream_infos()[0]
        self.input_shape = input_stream_info.shape
        print(f"[Hailo] 기대 입력 Shape: {self.input_shape}")

    def capture_and_infer(self):
        # Raspberry Pi Camera Module 3 GStreamer 파이프라인
        # Low Latency 원칙을 위해 appsink의 max-buffers=1 및 drop=true 설정 (최신 프레임만 유지)
        pipeline = (
            f"libcamerasrc ! video/x-raw, width={self.width}, height={self.height}, framerate={self.fps}/1 "
            f"! videoconvert ! appsink drop=true max-buffers=1"
        )
        print(f"[Camera] GStreamer 파이프라인 시작:\n {pipeline}")
        
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        if not cap.isOpened():
            print("[오류] Camera Module 3을 열 수 없습니다. (디버깅용 웹캠으로 전환 시도)")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return

        print("객체 탐지 루프 시작... (종료하려면 'q' 키를 누르세요)")
        
        if HAILO_AVAILABLE and self.infer_pipeline:
            with self.infer_pipeline:
                self._run_loop(cap)
        else:
            self._run_loop(cap)

        cap.release()
        cv2.destroyAllWindows()

    def _run_loop(self, cap):
        last_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[경고] 프레임을 읽어올 수 없습니다. 안전 모드 진입(Fail-Safe)")
                break
                
            # 카메라 가림 확인 (Fail-Safe 정책)
            if np.mean(frame) < 10:
                print("[경고] 영상이 너무 어둡습니다. 카메라가 가려졌을 수 있습니다.")

            # 1. 전처리
            input_data = self._preprocess(frame)
            
            # 2. 추론
            detections = []
            if HAILO_AVAILABLE and self.infer_pipeline:
                infer_results = self.infer_pipeline.infer(input_data)
                detections = self._postprocess(infer_results)
            else:
                # Mock 데이터: 화면 중앙에 임의의 사람(Person) 박스 생성
                h, w = frame.shape[:2]
                detections = [{
                    'class_id': 0, 
                    'confidence': 0.85, 
                    'bbox': [w//4, h//4, w//2, h//2], # [x_min, y_min, width, height]
                    'label': 'Person (Mock)'
                }]
            
            # 3. 오버레이 및 시각화
            curr_time = time.time()
            fps = 1.0 / (curr_time - last_time) if (curr_time - last_time) > 0 else 0
            last_time = curr_time
            
            self._draw_overlay(frame, detections, fps)
            
            try:
                cv2.imshow("Hailo-8 Obj Detection (Cam 3)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception:
                # Headless(GUI 없는 환경)일 경우 콘솔에 텍스트만 출력
                print(f"FPS: {fps:.1f} | Detections: {len(detections)}")

    def _preprocess(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if HAILO_AVAILABLE:
            # YOLO 모델이 요구하는 입력 크기로 리사이즈 (일반적으로 640x640)
            h, w = self.input_shape[1:3]
            frame_resized = cv2.resize(frame_rgb, (w, h))
            input_data = np.expand_dims(frame_resized, axis=0) 
            
            input_name = self.hef.get_input_vstream_infos()[0].name
            return {input_name: input_data}
            
        return frame_rgb

    def _postprocess(self, infer_results):
        # NOTE: 이 부분은 사용된 YOLO 버전에 따라 Output Tensor 구조가 달라집니다.
        # NMS(Non-Maximum Suppression)를 적용하거나 Hailo의 Post-processing 블록이 
        # 포함된 모델인 경우 직접 파싱합니다.
        # 여기서는 예시로 결과를 BBox 리스트로 변환하는 골격만 제공합니다.
        
        output_name = self.hef.get_output_vstream_infos()[0].name
        raw_outputs = infer_results[output_name]
        
        detections = []
        # TODO: 실제 YOLO 출력 텐서 파싱 및 NMS 로직 구현
        # 예시:
        # for box in raw_outputs[0]:
        #     if box.confidence > 0.5:
        #         detections.append({'class_id': ..., 'confidence': ..., 'bbox': ...})
        return detections

    def _draw_overlay(self, frame, detections, fps):
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        for det in detections:
            x, y, w, h = [int(v) for v in det['bbox']]
            label = f"{det['label']} {det['confidence']:.2f}"
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # YOLO 객체 탐지 모델 파일 (hef)
    hef_model_path = os.path.join(BASE_DIR, "..", "models", "yolov8s.hef")
    config_file_path = os.path.join(BASE_DIR, "..", "config", "calibration.json")
    
    os.makedirs(os.path.dirname(hef_model_path), exist_ok=True)
    
    demo = ObjectDetectionDemo(hef_model_path, config_file_path)
    demo.capture_and_infer()
