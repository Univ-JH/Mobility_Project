from ultralytics import YOLO

def main():
    # 세그멘테이션용 YOLO 모델 로드
    model = YOLO('yolo8n-seg.pt')

    # 모델 학습 시작
    results = model.train(
        data='data.yaml',            # yaml 파일 경로
        epochs=100,                  # 학습 반복 횟수
        imgsz=640,                   # 이미지 크기
        batch=16,                    # 배치 사이즈
        device='0',                  # GPU 사용
        project='kickboard_safety',  # 프로젝트(저장) 폴더명
        name='street_sidewalk_seg'   # 실험 이름
    )

    print("모델 학습 완료")

if __name__ == '__main__':
    main()