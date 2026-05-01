import json
import os
import glob
import cv2

def labelme2yolo_seg(json_folder, txt_folder, img_folder):
    # 클래스 매핑 딕셔너리
    class_mapping = {
        "Street": 0,
        "Sidewalk": 1
    }
    
    os.makedirs(txt_folder, exist_ok=True)
    
    # 폴더 내의 모든 json 파일 검색
    json_files = glob.glob(os.path.join(json_folder, "*.json"))
    
    print(f"대상 폴더: {json_folder}")
    print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.\n")
    
    if len(json_files) == 0:
        print("변환할 JSON 파일이 없습니다. 경로를 다시 확인해 주세요.")
        return

    for json_file in json_files:
        print(f"변환 중: {os.path.basename(json_file)}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        img_h = data.get('imageHeight')
        img_w = data.get('imageWidth')
        
        if img_h is None or img_w is None:
            img_name = os.path.basename(data.get('imagePath', ''))
            img_path = os.path.join(img_folder, img_name)
            img = cv2.imread(img_path)
            if img is not None:
                img_h, img_w, _ = img.shape
            else:
                print(f"[경고] 이미지 해상도를 찾을 수 없어 건너뜁니다: {img_path}")
                continue

        txt_name = os.path.splitext(os.path.basename(json_file))[0] + ".txt"
        txt_path = os.path.join(txt_folder, txt_name)
        
        valid_shapes_count = 0
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            for shape in data.get('shapes', []):
                label = shape.get('label')
                
                # 대소문자나 공백 문제 방지를 위해 strip() 처리 후 매핑 확인
                if label.strip() not in class_mapping:
                    continue
                
                class_id = class_mapping[label.strip()]
                points = shape.get('points', [])
                
                yolo_points = []
                for point in points:
                    x_norm = point[0] / img_w
                    y_norm = point[1] / img_h
                    yolo_points.append(f"{x_norm:.6f} {y_norm:.6f}")
                
                txt_file.write(f"{class_id} " + " ".join(yolo_points) + "\n")
                valid_shapes_count += 1
                
        print(f"  └─ 완료! (저장된 폴리곤 수: {valid_shapes_count}개)")

    print("\n 모든 변환 작업이 완료. 'yolo_labels' 폴더를 확인해 보세요.")

# ==========================================
# 실행 부분: 현재 파이썬 스크립트가 있는 폴더 기준
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))

# 현재 폴더 안에 JSON과 이미지가 모두 있다고 가정.
json_dir = current_dir 
img_dir = current_dir
# 변환된 TXT 파일은 현재 폴더 안의 'yolo_labels' 라는 새 폴더에 저장.
txt_dir = os.path.join(current_dir, 'yolo_labels')

labelme2yolo_seg(json_dir, txt_dir, img_dir)