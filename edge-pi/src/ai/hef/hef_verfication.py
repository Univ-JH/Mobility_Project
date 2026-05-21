import cv2
import os

# 1. 파일 절대 경로 설정 (반드시 본인의 라즈베리파이 경로에 맞게 수정!)
hef_path = "edge-pi/src/ai/hef/best.hef"
image_path = "edge-pi/src/ai/hef/test_road.jpg"
post_process_so = "/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libyolo_hailortpp_post.so"

# 2. 파일 존재 여부 사전 검증
if not os.path.exists(hef_path):
    print(f"에러: HEF 모델을 찾을 수 없습니다 -> {hef_path}")
    exit()
if not os.path.exists(image_path):
    print(f"에러: 테스트할 사진을 찾을 수 없습니다 -> {image_path}")
    exit()

# 3. GStreamer 파이프라인 구성 (416x416 해상도 강제 적용)
# video/x-raw 부분에 width=416, height=416을 추가하여 모델 입력 크기에 맞춥니다.
pipeline = (
    f"filesrc location={image_path} ! "
    "decodebin ! videoconvert ! "
    "video/x-raw, width=416, height=416, format=RGB ! " 
    f"hailonet hef-path={hef_path} ! "
    f"hailofilter so-path={post_process_so} ! "
    "videoconvert ! appsink sync=false"
)

print("파이프라인 초기화 및 NPU 로딩 중...")
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("파이프라인을 열 수 없습니다.")
    exit()

print("모델 정상 로드됨. 이미지 추론 및 후처리 진행 중...")
ret, frame = cap.read()

if ret:
    # 추론 결과가 반영된(바운딩 박스가 그려진) 이미지를 화면에 띄움
    cv2.imshow("Hailo 416x416 Custom Model Test", frame)
    print("결과가 화면에 표시되었습니다. 창을 닫으려면 아무 키나 누르세요.")
    cv2.waitKey(0)
else:
    print("이미지 프레임을 읽어오는 데 실패했습니다.")

# 자원 해제
cap.release()
cv2.destroyAllWindows()