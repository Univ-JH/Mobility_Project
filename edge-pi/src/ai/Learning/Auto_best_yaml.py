from ultralytics import YOLO

model = YOLO('yolov8n-seg.pt')

# iterations=30 이면 30개의 서로 다른 파라미터 조합을 테스트하며 최적의 값을 찾습니다.
# 시간이 오래 걸리므로, 에포크는 30~50 정도로 짧게 주고 경향성을 파악하는 용도로 씁니다.
model.tune(
    data='data.yaml', 
    epochs=50, 
    iterations=30, 
    optimizer='AdamW', 
    plots=False, 
    save=False, 
    val=False
)