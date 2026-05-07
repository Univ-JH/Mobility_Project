import argparse
import time
import lgpio

# --- 하드웨어 설정 ---
SERVO_PIN = 18
PWM_FREQ = 50 


MIN_PULSE = 1000   # 0도일 때의 펄스폭
MAX_PULSE = 2000   # 180도일 때의 펄스폭
# -----------------------------------------------------------

def set_angle(angle):
    if angle < 0 or angle > 180:
        print("⚠️ 에러: 각도는 0에서 180 사이여야 합니다.")
        return

    # 라즈베리 파이 5 GPIO 칩 열기
    try:
        h = lgpio.gpiochip_open(4)
    except lgpio.error:
        try:
            h = lgpio.gpiochip_open(0)
        except Exception as e:
            print(f"⚠️ 에러: GPIO 칩 연결 실패 ({e})")
            return

    try:
        # 1. 수정한 보정치를 사용하여 펄스 폭 계산
        # 0도 = MIN_PULSE, 180도 = MAX_PULSE가 되도록 매핑
        lgpio.gpio_claim_output(h, SERVO_PIN)
        pulse_width = MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE)
        
        # 2. Duty Cycle 계산 (20ms 주기에 대한 % 비율)
        duty_cycle = (pulse_width / 20000.0) * 100.0
        
        # 3. PWM 신호 출력
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, duty_cycle)
        
        print(f"✅ 목표 각도: {angle}도")
        print(f"📡 현재 설정된 펄스 폭: {int(pulse_width)}us (범위: {MIN_PULSE}~{MAX_PULSE})")
        print("🔧 조립을 위해 유지 중... 종료하려면 Ctrl+C를 누르세요.")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[종료] 사용자가 제어를 중단했습니다.")
    finally:
        # 종료 시 모터 힘을 완전히 뺌 (떨림 방지 및 과열 보호)
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
        lgpio.gpio_free(h, SERVO_PIN)
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("angle", type=float, help="이동시킬 목표 각도 (0 ~ 180)")
    args = parser.parse_args()
    
    set_angle(args.angle)