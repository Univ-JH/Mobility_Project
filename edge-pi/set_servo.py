import argparse
import time
import lgpio

SERVO_PIN = 18
PWM_FREQ = 50  # 서보모터의 표준 주파수는 50Hz 입니다.

def set_angle(angle):
    # 각도 유효성 검사
    if angle < 0 or angle > 180:
        print("⚠️ 에러: 각도는 0에서 180 사이여야 합니다.")
        return

    # 라즈베리 파이 5의 메인 GPIO 칩 열기 (보통 chip 4가 40핀 헤더를 담당합니다)
    try:
        h = lgpio.gpiochip_open(4)
    except lgpio.error:
        try:
            h = lgpio.gpiochip_open(0) # 호환성을 위해 0번 칩도 시도
        except Exception as e:
            print(f"⚠️ 에러: GPIO 칩을 열 수 없습니다. ({e})")
            return

    try:
        # 1. 각도를 펄스 폭(500~2500us)으로 변환
        pulse_width = 500 + (angle / 180.0) * 2000
        
        # 2. 펄스 폭을 Duty Cycle(%)로 변환
        # 50Hz 주파수에서 1주기는 20ms(20,000us) 입니다.
        # 즉, (현재 펄스폭 / 20000) * 100을 하면 % 값이 나옵니다.
        duty_cycle = (pulse_width / 20000.0) * 100.0
        
        # 3. 모터 회전 명령 (PWM 신호 쏘기)
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, duty_cycle)
        
        print(f"✅ 모터가 {angle}도로 이동했습니다.")
        print(f"   (펄스폭: {int(pulse_width)}us -> 듀티사이클: {duty_cycle:.2f}%)")
        
        # 사용자가 끌 때까지 모터가 풀리지 않도록(토크 유지) 무한 대기
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[종료] 사용자가 모터 제어를 해제했습니다.")
    finally:
        # 종료 시 모터 신호 차단 (Duty Cycle을 0으로 만들어 모터를 부드럽게 품)
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
        
        # 핀 및 칩 점유 해제 (아주 중요!)
        lgpio.gpio_free(h, SERVO_PIN)
        lgpio.gpiochip_close(h)

if __name__ == "__main__":
    # 터미널에서 입력받은 매개변수(인자) 처리
    parser = argparse.ArgumentParser(description="서보모터 수동 각도 조절 툴 (lgpio 버전)")
    parser.add_argument("angle", type=float, help="이동시킬 목표 각도 (0 ~ 180)")
    args = parser.parse_args()
    
    set_angle(args.angle)