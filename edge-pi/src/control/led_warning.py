import threading
import lgpio

# 전방 핀 설정
try:
    from .control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN
except ImportError:
    LED_R_PIN = 12
    LED_G_PIN = 13
    LED_B_PIN = 19

# [핵심 수정] 후방 핀 설정: REAR_LED_PIN이 없으면 사용자님의 원래 이름인 LED_BAR_PIN을 찾습니다!
try:
    from .control_config import REAR_LED_PIN
except ImportError:
    try:
        from .control_config import LED_BAR_PIN as REAR_LED_PIN
    except ImportError:
        REAR_LED_PIN = 17

PWM_FREQ = 1000

class RearApproachLED:
    def __init__(self):
        self.lock = threading.Lock()
        self._active = False
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)
                
        # 전후방 핀 모두 출력 모드 셋팅
        for pin in [LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN]:
            lgpio.gpio_claim_output(self.h, pin)
            
        self.clear()
        print(f"💡 [LED] 전방 RGB(12,13,19) 및 후방 레드바(핀: {REAR_LED_PIN}) 모듈 준비 완료")

    def _set_rgb_color(self, r_duty, g_duty, b_duty):
        """전방 RGB 색상 제어 (반전 전압)"""
        lgpio.tx_pwm(self.h, LED_R_PIN, PWM_FREQ, 100 - r_duty)
        lgpio.tx_pwm(self.h, LED_G_PIN, PWM_FREQ, 100 - g_duty)
        lgpio.tx_pwm(self.h, LED_B_PIN, PWM_FREQ, 100 - b_duty)

    def warn_rear(self):
        """경고 점등: 앞은 빨강, 뒤는 레드바 ON"""
        if self._active:
            return
        with self.lock:
            self._active = True
            self._set_rgb_color(100, 0, 0)
            lgpio.gpio_write(self.h, REAR_LED_PIN, 1)

    def clear(self):
        """모두 소등"""
        if not getattr(self, '_active', True):
            return
        with self.lock:
            self._active = False
            self._set_rgb_color(0, 0, 0)
            lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    def test_colors(self):
        """전방의 다양한 색상 확인용"""
        import time
        with self.lock:
            print("  ➔ 전방: 초록색 켜짐 🟢")
            self._set_rgb_color(0, 100, 0)
            time.sleep(1.5)
            print("  ➔ 전방: 노란색 켜짐 🟡")
            self._set_rgb_color(100, 70, 0)
            time.sleep(1.5)
            self._set_rgb_color(0, 0, 0)

    def test_rear_only(self):
        """[신규 추가] 후방 8구 레드바만 확실하게 켜보는 함수"""
        import time
        with self.lock:
            print(f"  ➔ 후방 8구 레드바 ON 🔴 (사용 중인 핀: {REAR_LED_PIN})")
            lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
            time.sleep(2.0)
            print("  ➔ 후방 8구 레드바 OFF 🌑")
            lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    def cleanup(self):
        self._active = False
        self._set_rgb_color(0, 0, 0)
        lgpio.gpio_write(self.h, REAR_LED_PIN, 0)
        
        lgpio.tx_pwm(self.h, LED_R_PIN, PWM_FREQ, 0)
        lgpio.tx_pwm(self.h, LED_G_PIN, PWM_FREQ, 0)
        lgpio.tx_pwm(self.h, LED_B_PIN, PWM_FREQ, 0)
        
        for pin in [LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN]:
            lgpio.gpio_free(self.h, pin)
        lgpio.gpiochip_close(self.h)