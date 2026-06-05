import time
import lgpio
import threading

# ==========================================
# 1. 핀 번호 설정 (라즈베리 파이 5 하드웨어 핀맵 기준)
# ==========================================
# ELB050090 (RGB 풀컬러 모듈) - 공통 양극(Common Anode)
# 주의: 이 모듈은 0일 때 켜지고, 100(또는 1)일 때 꺼집니다.
RGB_R_PIN = 12  # 물리 32번 (BCM 12)
RGB_G_PIN = 13  # 물리 33번 (BCM 13)
RGB_B_PIN = 19  # 물리 35번 (BCM 19)

# ELB050075 (8 LED 레드 바 모듈)
# 이 모듈은 일반적인 1일 때 켜지고, 0일 때 꺼집니다.
LED_BAR_PIN = 17 # 물리 11번 (BCM 17)

PWM_FREQ = 1000 # RGB 부드러운 제어를 위한 주파수

# ==========================================
# 2. GPIO 초기화 및 안전 자물쇠
# ==========================================
lock = threading.Lock()

try:
    h = lgpio.gpiochip_open(4)
except:
    h = lgpio.gpiochip_open(0)

# 핀 출력 모드 설정
for pin in [RGB_R_PIN, RGB_G_PIN, RGB_B_PIN, LED_BAR_PIN]:
    lgpio.gpio_claim_output(h, pin)

# ==========================================
# 3. 제어 함수 정의
# ==========================================
def set_rgb_color(r_duty, g_duty, b_duty):
    """
    RGB 모듈의 색상을 설정합니다. (공통 양극 방식이라 값을 뒤집어서 입력)
    - duty: 0(가장 밝음) ~ 100(꺼짐)
    """
    with lock:
        # 사용자는 0~100(밝기)로 입력하지만, 하드웨어는 반대로 인식하도록 변환
        lgpio.tx_pwm(h, RGB_R_PIN, PWM_FREQ, 100 - r_duty)
        lgpio.tx_pwm(h, RGB_G_PIN, PWM_FREQ, 100 - g_duty)
        lgpio.tx_pwm(h, RGB_B_PIN, PWM_FREQ, 100 - b_duty)

def set_led_bar(is_on):
    """
    8 LED 레드 바를 켜거나 끕니다.
    """
    with lock:
        lgpio.gpio_write(h, LED_BAR_PIN, 1 if is_on else 0)

def off_all():
    """모든 LED 끄기"""
    set_rgb_color(0, 0, 0) # RGB 끄기 (밝기 0)
    set_led_bar(False)     # 레드 바 끄기

# ==========================================
# 4. 메인 테스트 시나리오
# ==========================================
print("💡 LED 모듈 통합 테스트를 시작합니다!")
print("먼저 모든 LED를 끄고 초기화합니다...")
off_all()
time.sleep(1)

try:
    # --- [시나리오 1: 8 LED 레드 바 점멸 테스트] ---
    print("\n[테스트 1] 브레이크 등(8 LED 바) 깜빡임 테스트")
    for i in range(3):
        print("  ➔ 레드 바 ON 🔴")
        set_led_bar(True)
        time.sleep(0.5)
        print("  ➔ 레드 바 OFF 🌑")
        set_led_bar(False)
        time.sleep(0.5)

    time.sleep(1)

    # --- [시나리오 2: RGB 풀컬러 모듈 색상 테스트] ---
    print("\n[테스트 2] 자전거 상태(RGB) 단색 표시 테스트")
    colors = {
        "빨강 (위험)": (100, 0, 0),
        "초록 (정상)": (0, 100, 0),
        "파랑 (대기)": (0, 0, 100),
        "노랑 (경고)": (100, 100, 0), # 빨강 + 초록
        "보라 (특수)": (100, 0, 100), # 빨강 + 파랑
        "흰색 (전체)": (100, 100, 100)
    }

    for name, (r, g, b) in colors.items():
        print(f"  ➔ {name} 켜짐")
        set_rgb_color(r, g, b)
        time.sleep(1.5)

    # --- [시나리오 3: 숨쉬기 모드 (부드러운 PWM 제어)] ---
    print("\n[테스트 3] 파란색 숨쉬기 모드 (Fade in/out) 테스트")
    for _ in range(2):
        # 점점 밝아지기
        for i in range(0, 101, 5): 
            set_rgb_color(0, 0, i)
            time.sleep(0.05)
        # 점점 어두워지기
        for i in range(100, -1, -5):
            set_rgb_color(0, 0, i)
            time.sleep(0.05)

    print("\n✅ 모든 LED 테스트가 완료되었습니다!")

except KeyboardInterrupt:
    print("\n🛑 테스트가 사용자에 의해 강제 종료되었습니다.")

finally:
    # 프로그램 종료 시 무조건 모든 불을 끄고 핀 반환
    off_all()
    
    # PWM 모드 해제 및 핀 초기화
    lgpio.tx_pwm(h, RGB_R_PIN, PWM_FREQ, 0)
    lgpio.tx_pwm(h, RGB_G_PIN, PWM_FREQ, 0)
    lgpio.tx_pwm(h, RGB_B_PIN, PWM_FREQ, 0)
    
    for pin in [RGB_R_PIN, RGB_G_PIN, RGB_B_PIN, LED_BAR_PIN]:
        lgpio.gpio_free(h, pin)
    lgpio.gpiochip_close(h)
    print("🧹 LED 리소스 안전 반환 완료")