import cv2

pipeline = (
    "filesrc location=test_road.jpg ! "
    "decodebin ! videoconvert ! video/x-raw,format=RGB ! "
    "hailonet hef-path=road_surface_model.hef ! "
    "hailofilter so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libyolo_hailortpp_post.so ! "
    "videoconvert ! appsink"
)

# OpenCV로 파이프라인 실행
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("파이프라인을 열 수 없습니다.")
    exit()

ret, frame = cap.read()
if ret:
    # 객체 탐지 바운딩 박스가 그려진 결과 이미지를 화면에 출력
    cv2.imshow("Hailo Custom Model Test", frame)
    cv2.waitKey(0)

cap.release()
cv2.destroyAllWindows()