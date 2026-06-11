# 도커 내부에서 해당 코드를 실행해야하므로 (hailo_virtualenv)가 활성화된 상태에서 실행해야 함.
# 코드 실행전, onnx와 train 이미지 폴더가 해당 위치에 미리 복사되어 있어야 함.
import subprocess
import os

def run_command(command):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, check=True)
    return result

def main():
    # 설정값
    model_name = "yolov8n_seg"
    onnx_file = "best.onnx"
    calib_path = "/local/workspace/train_images"
    
    try:
        # 1. 파싱 (Parsing)
        run_command(f"hailomz parse --hw-arch hailo8l --ckpt {onnx_file} {model_name}")
        
        # 2. 최적화 (Optimize)
        run_command(f"hailomz optimize {model_name} --hw-arch hailo8l --har {model_name}.har --calib-path {calib_path} --classes 1")
        
        # 3. 컴파일 (Compile)
        run_command(f"hailomz compile {model_name} --hw-arch hailo8l --har {model_name}.har")
        
        print("HEF 변환 자동화 완료")
        
    except subprocess.CalledProcessError as e:
        print(f"변환 도중 에러 발생: {e}")

if __name__ == "__main__":
    main()