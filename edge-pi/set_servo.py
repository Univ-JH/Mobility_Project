# set_servo.py (프로젝트 최상단 폴더에 위치)
import argparse
import time
import pigpio

SERVO_PIN = 18

def set_angle(angle):
    # 각도 유효성 검사
    if angle < 0 or angle > 180:
        print("⚠️ 에러: 각도는 0에서 180 사이여야 합니다.")
        return

    # pigpio 데몬 연결
    pi = pigpio.pi()
    if not pi.connected:
        print("⚠️ 에러: pigpio 데몬에 연결할 수 없습니다. 'sudo pigpiod'를 실행했는지 확인하세요.")
        return

    try:
        # 각도를 펄스 폭(500~2500)으로 변환
        pulse_width = 500 + (angle / 180.0) * 2000
        
        # 모터 회전 명령
        pi.set_servo_pulsewidth(SERVO_PIN, pulse_width)
        print(f"✅ 모터가 {angle}도로 이동했습니다. (펄스폭: {int(pulse_width)}us)")
        print("🔧 현재 위치를 단단하게 유지 중입니다. 조립/확인이 끝나면 [Ctrl+C]를 눌러 모터를 풀어주세요.")
        
        # 사용자가 끌 때까지 모터가 풀리지 않도록(토크 유지) 무한 대기
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[종료] 사용자가 모터 제어를 해제했습니다.")
    finally:
        # 종료 시 모터 신호 차단 (모터가 부드럽게 풀림)
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()

if __name__ == "__main__":
    # 터미널에서 입력받은 매개변수(인자) 처리
    parser = argparse.ArgumentParser(description="서보모터 수동 각도 조절 툴")
    parser.add_argument("angle", type=float, help="이동시킬 목표 각도 (0 ~ 180)")
    args = parser.parse_args()
    
    set_angle(args.angle)