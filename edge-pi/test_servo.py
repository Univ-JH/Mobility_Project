import time
import lgpio

SERVO_PIN = 18

# 라즈베리 파이 5의 하드웨어 PWM 전용 컨트롤러(칩 2번)를 강제로 고정하여 엽니다.
try:
    h = lgpio.gpiochip_open(2)
    print("🤖 [시스템] 라즈베리 파이 5 전용 GPIO 칩(2번) 오픈 성공")
except Exception:
    try:
        h = lgpio.gpiochip_open(4)
    except Exception:
        h = lgpio.gpiochip_open(0)

try:
    lgpio.gpio_free(h, SERVO_PIN)
except: pass

lgpio.gpio_claim_output(h, SERVO_PIN, 0)

print("⚡ 소프트웨어 강제 펄스 테스트를 시작합니다.")
print("배선과 전원이 정상이라면 모터가 반드시 회전해야 합니다.\n")

def pulse_servo(target_ms):
    # 서보모터가 인식할 수 있는 정밀한 펄스를 수동으로 만듭니다.
    for _ in range(30): # 30번 반복 수행
        lgpio.gpio_write(h, SERVO_PIN, 1)
        time.sleep(target_ms / 1000.0)
        lgpio.gpio_write(h, SERVO_PIN, 0)
        time.sleep((20.0 - target_ms) / 1000.0)

try:
    while True:
        cmd = input("1: 0도 이동 / 2: 90도 이동 / 3: 180도 이동 / q: 종료 -> ")
        if cmd == '1':
            print("➔ 0도 제어 신호 송출 (0.85ms 펄스)")
            pulse_servo(0.85)
        elif cmd == '2':
            print("➔ 90도 제어 신호 송출 (1.5ms 펄스)")
            pulse_servo(1.5)
        elif cmd == '3':
            print("➔ 180도 제어 신호 송출 (2.15ms 펄스)")
            pulse_servo(2.15)
        elif cmd.lower() == 'q':
            break
finally:
    lgpio.gpio_free(h, SERVO_PIN)
    lgpio.gpiochip_close(h)
    print("🧹 리소스 반환 완료.")