import argparse
import time
import lgpio

# --- 하드웨어 설정 ---
SERVO_PIN = 18
PWM_FREQ = 50 

MIN_PULSE = 850   # 0도
MAX_PULSE = 2150  # 180도
# ----------------------------

def set_angle(angle):
    if angle < 0 or angle > 180:
        print("⚠️ 에러: 각도는 0에서 180 사이여야 합니다.")
        return

    try:
        h = lgpio.gpiochip_open(4)
    except:
        h = lgpio.gpiochip_open(0)

    try:
        # 1. 펄스 폭 및 Duty Cycle 계산
        lgpio.gpio_claim_output(h, SERVO_PIN)
        pulse_width = MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE)
        duty_cycle = (pulse_width / 20000.0) * 100.0
        
        # 2. 모터 이동 명령
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, duty_cycle)
        print(f"✅ {angle}도로 이동 중...")
        
        # 3. [핵심] 모터가 이동할 시간 확보 (1초)
        time.sleep(1.0)
        
        # 4. [핵심] 신호 차단 (Duty Cycle 0) -> 여기서 떨림이 멈춥니다.
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
        print(f"💤 이동 완료 및 신호 차단")

    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")
    finally:
        # 칩 리소스 해제
        lgpio.gpio_free(h, SERVO_PIN)
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("angle", type=float)
    args = parser.parse_args()
    set_angle(args.angle)