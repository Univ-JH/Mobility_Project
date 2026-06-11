from ultralytics import YOLO
import cv2

# 1. 학습된 모델 가중치 불러오기
model_path = 'best.pt' 
model = YOLO(model_path)

# 2. 테스트할 이미지 경로 설정
test_image_path = 'test_sample.jpg' 

# 3. 모델 추론 (예측) 수행
# conf=0.5 : 신뢰도(Confidence)가 50% 이상인 결과만 표시. (필요에 따라 조절)
# save=True : 결과를 'runs/segment/predict' 폴더에 이미지로 저장.
# show=True : 결과를 실행 즉시 화면에 팝업창으로 띄워 보여줌.
results = model.predict(source=test_image_path, conf=0.5, save=True, show=True)

cv2.waitKey(0)
cv2.destroyAllWindows()

print("테스트 완료")