from ultralytics import YOLO

def main():
    # 1. 모델 불러오기
    model = YOLO('yolo8n-seg.pt') 

    # 2. 하이퍼파라미터를 조절하여 학습 실행
    results = model.train(
    data='data.yaml',
    epochs=150,     
    imgsz=640,

    # --- 손실 가중치 조절 (객체 탐지 강화) ---
    box=8.5,              # 기본값 7.5 -> 8.5
    cls=1.0,              # 기본값 0.5 -> 1.0

    # --- 데이터 증강 강화 (적은 데이터 극복) ---
    hsv_h=0.015,          # 색상 변환
    hsv_s=0.7,            # 채도 변환 (강하게)
    hsv_v=0.4,            # 명도 변환 (강하게)
    degrees=10.0,         # 10도 범위 내에서 회전
    translate=0.1,        # 10% 범위 내에서 이미지 이동
    flipud=0.0,           # 상하 반전
    fliplr=0.5,           # 좌우 반전 (50% 확률)
    mosaic=1.0            # 모자이크 증강 100%
    )

if __name__ == '__main__':
    main()