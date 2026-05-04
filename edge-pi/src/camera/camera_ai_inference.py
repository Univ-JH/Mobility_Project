import cv2
import numpy as np
from picamera2 import Picamera2
import time

# 1. Picamera2 초기화 및 설정
picam2 = Picamera2()

# 카메라 모듈 3의 해상도 및 프레임 설정 (처리 속도를 위해 적절한 해상도 선택)
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

# 2. AI 모델을 위한 프레임 전처리 함수
def preprocess_frame(frame, target_size=(224, 224)):
    """
    AI 가속기 모델(Edge AI) 추론을 위해 프레임을 전처리하는 함수
    - target_size: 사용하시는 판별 모델의 입력 사이즈에 맞게 수정하세요.
    """
    # BGR(OpenCV 기본)에서 RGB로 색상 공간 변환
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 모델 입력 크기에 맞춰 리사이징
    resized_frame = cv2.resize(rgb_frame, target_size)
    
    # 정규화 (Normalization): 픽셀 값을 0.0 ~ 1.0 범위로 변환 (모델 사양에 따라 조정 필요)
    normalized_frame = resized_frame.astype(np.float32) / 255.0
    
    # 차원 추가 (Batch dimension): (Height, Width, Channels) -> (1, Height, Width, Channels)
    # 딥러닝 모델은 보통 배치 단위로 입력을 받기 때문에 차원 확장이 필요합니다.
    input_tensor = np.expand_dims(normalized_frame, axis=0)
    
    return input_tensor

print("카메라 작동을 시작합니다. 종료하려면 'q'를 누르세요.")

try:
    while True:
        # 3. 실시간 프레임 캡처 (Numpy 배열 형태)
        frame = picam2.capture_array()

        # 4. 캡처된 프레임을 AI 가속기 추론용으로 전처리
        ai_input_data = preprocess_frame(frame, target_size=(224, 224))
        
        # ---------------------------------------------------------
        # 이 부분에 AI 가속기(예: TensorFlow Lite) 추론 코드를 삽입하세요!
        # 예시:
        # interpreter.set_tensor(input_details[0]['index'], ai_input_data)
        # interpreter.invoke()
        # prediction = interpreter.get_tensor(output_details[0]['index'])
        # ---------------------------------------------------------

        # 5. 영상 출력 (디버깅 및 확인용)
        cv2.imshow("Mobility_Project - Bottom Camera", frame)

        # 'q' 키를 누르면 루프 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("사용자에 의해 프로그램이 종료되었습니다.")

finally:
    # 6. 자원 해제
    picam2.stop()
    cv2.destroyAllWindows()
    print("카메라 및 윈도우가 정상적으로 종료되었습니다.")