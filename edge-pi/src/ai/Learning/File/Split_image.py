import os
import shutil
import random

# ================= 설정 부분 =================
# 1. 바탕화면 경로 자동 인식
desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')

# 2. 현재 작업 폴더 설정
IMAGE_DIR = '.'                                      # 현재 폴더 (원본 이미지들이 있는 곳)
LABEL_DIR = os.path.join('.', 'json', 'yolo_labels') # 현재 폴더 안의 json/yolo_labels 경로

# 3. 데이터가 저장될 최종 목적지 (바탕화면 > 학습 테스트 > dataset)
OUTPUT_DIR = os.path.join(desktop_path, '학습 테스트', 'dataset')

# 4. Train 데이터 비율
TRAIN_RATIO = 0.7            
# =============================================

def split_dataset():
    print(" 데이터셋 7:3 분할 작업을 시작합니다...")

    # 1. 라벨 폴더가 실제로 있는지 확인
    if not os.path.exists(LABEL_DIR):
        print(f" 에러: '{LABEL_DIR}' 폴더를 찾을 수 없습니다.")
        print("현재 파이썬 파일이 '1' 또는 '사진' 폴더 최상단에 있는지 확인해 주세요.")
        return

    # 2. 목적지(dataset) 폴더 구조 만들기
    dirs_to_make = [
        os.path.join(OUTPUT_DIR, 'images', 'train'),
        os.path.join(OUTPUT_DIR, 'images', 'val'),
        os.path.join(OUTPUT_DIR, 'labels', 'train'),
        os.path.join(OUTPUT_DIR, 'labels', 'val')
    ]
    
    for d in dirs_to_make:
        os.makedirs(d, exist_ok=True)

    # 3. 라벨(txt) 파일 목록 불러오기
    label_files = [f for f in os.listdir(LABEL_DIR) if f.endswith('.txt')]
    valid_pairs = []
    
    # 4. 라벨 파일과 이름이 똑같은 이미지 파일 찾기
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    for label_file in label_files:
        base_name = os.path.splitext(label_file)[0]
        
        img_file = None
        for ext in image_extensions:
            if os.path.exists(os.path.join(IMAGE_DIR, base_name + ext)):
                img_file = base_name + ext
                break
                
        if img_file:
            valid_pairs.append((img_file, label_file))
        else:
            print(f"누락 알림: {label_file} 에 대응하는 이미지를 찾지 못했습니다.")

    if not valid_pairs:
        print(" 복사할 데이터쌍이 없습니다. 이미지와 라벨 파일 이름을 다시 확인해 주세요.")
        return

    # 5. 파일 무작위 섞기 및 7:3 나누기
    random.shuffle(valid_pairs)
    split_index = int(len(valid_pairs) * TRAIN_RATIO)
    train_pairs = valid_pairs[:split_index]
    val_pairs = valid_pairs[split_index:]

    # 6. 파일 복사 함수
    def copy_files(pairs, split_type):
        for img_file, label_file in pairs:
            # 이미지 복사
            src_img = os.path.join(IMAGE_DIR, img_file)
            dst_img = os.path.join(OUTPUT_DIR, 'images', split_type, img_file)
            shutil.copy(src_img, dst_img)
            
            # 라벨 복사
            src_label = os.path.join(LABEL_DIR, label_file)
            dst_label = os.path.join(OUTPUT_DIR, 'labels', split_type, label_file)
            shutil.copy(src_label, dst_label)

    # 7. 실제 복사 실행
    print(f"✅ 총 {len(valid_pairs)}개의 정상 데이터쌍을 찾았습니다.")
    
    print(f"📦 Train 데이터 ({len(train_pairs)}개) 복사 중...")
    copy_files(train_pairs, 'train')
    
    print(f"📦 Val 데이터 ({len(val_pairs)}개) 복사 중...")
    copy_files(val_pairs, 'val')
    
    print(f"\n작업 완료! 바탕화면의 [학습 테스트/dataset] 폴더에 데이터가 준비되었습니다.")

if __name__ == '__main__':
    split_dataset()