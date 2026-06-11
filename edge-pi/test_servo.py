import time
import lgpio
import threading

# 사용자님이 확인해주신 BCM 18번 핀 매핑 반영
SERVO_PIN = 18
PWM_FREQ = 50
SERVO_MIN_PULSE = 850
SERVO_MAX_PULSE = 2150

# 안전 자물쇠 적용
lock = threading.Lock()

try:
    h = lgpio.gpiochip_open(4)
except Exception:
    h = lgpio.gpiochip_open(0)

# ==========================================
# ✨ [핀 잠김 방어벽] 이전 실행 실패로 핀이 묶여있다면 강제로 청소합니다.
# ==========================================
try:
    lgpio.gpio_free(h, SERVO_PIN)
except Exception:
    pass

# 안전하게 초기값을 0으로 밀어 넣으면서 출력 핀으로 선언
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
        time.sleep(1.0)                        # 1초간 힘을 주고 각도 유지
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0) # ✨ 모터 보호를 위해 제동 후 즉시 전력 차단
        print(f"   ➔ {angle}도 이동 완료 및 모터 전력 차단 (떨림 방지)")

print("🕹️ 브레이크 서보모터 영점 조절 테스트 시작")
print("⚠️ 주의: 모터에서 '징~' 하고 떠는 소리가 계속 나면 즉시 0도를 입력하거나 Ctrl+C로 종료하세요!\n")

try:
    while True:
        user_input = input("이동할 각도를 입력하세요 (0 ~ 180) / 종료는 q: ")
        if user_input.lower() == 'q':
            break
            
        try:
            angle = float(user_input)
            move_servo(angle)
        except ValueError:
            print("숫자만 입력해 주세요.")

except KeyboardInterrupt:
    print("\n👋 사용자에 의해 테스트가 중단되었습니다.")
finally:
    # 종료 시 자원 청소를 확실하게 마쳐서 다음 실행 때 절대 안 멈추게 만듭니다.
    try:
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
        lgpio.gpio_free(h, SERVO_PIN)
        lgpio.gpiochip_close(h)
    except Exception:
        pass
    print("🛑 테스트 안전 종료 (모든 하드웨어 리소스 반환 완료)")