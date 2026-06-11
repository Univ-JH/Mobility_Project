import time
import lgpio

SERVO_PIN = 18

# GPIO 칩 초기화 (파이 5 기준)
try:
    h = lgpio.gpiochip_open(2)
except:
    try: h = lgpio.gpiochip_open(4)
    except: h = lgpio.gpio_open(0)

lgpio.gpio_claim_output(h, SERVO_PIN, 0)

def manual_pulse(target_ms):
    """서보모터 펄스 신호 생성"""
    for _ in range(25): 
        lgpio.gpio_write(h, SERVO_PIN, 1)
        time.sleep(target_ms / 1000.0)
        lgpio.gpio_write(h, SERVO_PIN, 0)
        time.sleep((20.0 - target_ms) / 1000.0)

try:
    while True:
        cmd = input("1: 풀림(30도) / 2: 잠김(110도) / q: 종료 -> ")
        if cmd == '1':
            print("➔ 30도(풀림) 신호 송출...")
            manual_pulse(0.83) # 30도 설정
        elif cmd == '2':
            print("➔ 110도(잠김) 신호 송출...")
            manual_pulse(1.72) # 110도 설정
        elif cmd.lower() == 'q':
            break
finally:
    lgpio.gpio_free(h, SERVO_PIN)
    lgpio.gpiochip_close(h)