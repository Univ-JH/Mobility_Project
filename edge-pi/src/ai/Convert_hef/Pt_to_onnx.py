from ultralytics import YOLO

# 본인의 최종 학습 가중치 경로를 입력하세요.
model = YOLO('yolov8n-seg_Final.pt') 
model.export(format="onnx") # 동일 경로에 best.onnx 가 생성됩니다.