import time
import lgpio

SERVO_PIN = 18

# 파이 5는 2번 칩이 국룰입니다.
try:
    h = lgpio.gpiochip_open(2)
except:
    try: h = lgpio.gpiochip_open(4)
    except: h = lgpio.gpiochip_open(0)

try:
    lgpio.gpio_free(h, SERVO_PIN)
except: pass

lgpio.gpio_claim_output(h, SERVO_PIN, 0)

print("⚡ [테스트] 소프트웨어 수동 펄스 강제 주입 시작")
print("신호선(12번 핀) 매핑이 맞다면 모터가 반드시 반응해야 합니다.\n")

def manual_pulse(target_ms):
    """서보모터가 인식할 수 있는 정밀한 펄스 간격을 수동으로 생성합니다."""
    # 0.02초(50Hz) 간격으로 25번 신호를 밀어 넣어 모터를 강제로 회전시킵니다.
    for _ in range(25): 
        lgpio.gpio_write(h, SERVO_PIN, 1)          # 신호 HIGH (전기 켜기)
        time.sleep(target_ms / 1000.0)             # 각도 결정 시간 유지
        lgpio.gpio_write(h, SERVO_PIN, 0)          # 신호 LOW (전기 끄기)
        time.sleep((20.0 - target_ms) / 1000.0)    # 남은 주기 쉬어주기

try:
    while True:
        cmd = input("1: 최소각(0도) / 2: 중간각(90도) / 3: 최대각(180도) / q: 종료 -> ")
        if cmd == '1':
            print("➔ 0도 강제 신호 송출 중...")
            manual_pulse(0.85)
        elif cmd == '2':
            print("➔ 90도 강제 신호 송출 중...")
            manual_pulse(1.5)
        elif cmd == '3':
            print("➔ 180도 강제 신호 송출 중...")
            manual_pulse(2.15)
        elif cmd.lower() == 'q':
            break
finally:
    lgpio.gpio_free(h, SERVO_PIN)
    lgpio.gpiochip_close(h)
    print("🧹 리소스 반환 완료.")