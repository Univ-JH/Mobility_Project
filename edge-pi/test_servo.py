import time
import lgpio
import threading

SERVO_PIN = 18
PWM_FREQ = 50
SERVO_MIN_PULSE = 850
SERVO_MAX_PULSE = 2150

# 안전 자물쇠 적용
lock = threading.Lock()

try:
    h = lgpio.gpiochip_open(4)
except:
    h = lgpio.gpiochip_open(0)

# 혹시 이전에 프로그램이 튕겨서 핀이 잠겨있다면 강제로 풀어줍니다.
try:
    lgpio.gpio_free(h, SERVO_PIN)
except:
    pass

# 안전하게 초기값 0(로우 전압)을 주면서 아웃풋 핀으로 선언합니다.
lgpio.gpio_claim_output(h, SERVO_PIN, 0)

def calculate_duty(angle):
    if angle < 0: angle = 0
    if angle > 180: angle = 180
    pw = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
    return (pw / 20000.0) * 100.0

def move_servo(angle):
    with lock:
        duty = calculate_duty(angle)
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, duty)
        time.sleep(1.0) # 1초간 힘을 주고 각도 유지
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0) # 모터 보호를 위해 힘 풀기
        print(f"   ➔ {angle}도 이동 완료 및 모터 전력 차단")

print("🕹️ 브레이크 서보모터 영점 조절 테스트")
print("⚠️ 주의: 모터에서 '징~' 하고 떠는 소리가 계속 나면 즉시 0도를 입력하거나 강제 종료하세요!\n")

try:
    while True:
        user_input = input("이동할 각도를 입력하세요 (0 ~ 180) / 종료는 q: ")
        if user_input.lower() == 'q':
            break
            
        try:
            angle = float(user_input)
            move_servo(angle)
        except ValueError:
            print("숫자만 입력해주세요.")

except KeyboardInterrupt:
    pass
finally:
    # 종료 시 무조건 브레이크 풀기
    lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
    lgpio.gpio_free(h, SERVO_PIN)
    lgpio.gpiochip_close(h)
    print("\n🛑 테스트 안전 종료 (리소스 반환)")    