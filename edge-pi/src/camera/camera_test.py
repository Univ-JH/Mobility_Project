import cv2
from picamera2 import Picamera2

# 1. Picamera2 초기화
picam2 = Picamera2()

# 2. 해상도 설정 (테스트용이므로 화면에 띄우기 적당한 640x480으로 설정)
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)

# 3. 카메라 구동 시작
picam2.start()
print("카메라 테스트를 시작합니다.")
print("영상 창을 클릭한 후 영문 'q' 키를 누르면 안전하게 종료됩니다.")

try:
    while True:
        # 4. 카메라로부터 실시간 프레임 캡처 (Numpy 배열)
        frame = picam2.capture_array()

        # 5. 캡처된 프레임을 화면에 출력
        cv2.imshow("Camera Test - Mobility_Project", frame)

        # 6. 'q' 키 입력 감지 시 루프 탈출
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("터미널에서 강제 종료(Ctrl+C) 되었습니다.")

finally:
    # 7. 프로그램 종료 시 반드시 하드웨어 자원 및 창 해제
    picam2.stop()
    cv2.destroyAllWindows()
    print("카메라 및 윈도우가 정상적으로 종료되었습니다.")