import lgpio
from .control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN


class RearApproachLED:
    """전방 RGB LED — 후방 차량 고속 접근 경고 표시기.

    후방 접근 감지 시 빨간색 점등, 평상시 소등.
    lgpio 핀은 BCM 번호 기준 (물리 핀 32/33/35).
    """

    def __init__(self):
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)

        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN):
            lgpio.gpio_claim_output(self.h, pin, 0)

        self._active = False
        print("💡 전방 RGB LED 경고등 준비 완료")

    def warn_rear(self):
        """후방 접근 경고 — 빨간색 점등."""
        if self._active:
            return
        lgpio.gpio_write(self.h, LED_R_PIN, 1)
        lgpio.gpio_write(self.h, LED_G_PIN, 0)
        lgpio.gpio_write(self.h, LED_B_PIN, 0)
        self._active = True
        print("🔴 [LED] 후방 차량 접근 경고")

    def clear(self):
        """LED 소등."""
        if not self._active:
            return
        lgpio.gpio_write(self.h, LED_R_PIN, 0)
        lgpio.gpio_write(self.h, LED_G_PIN, 0)
        lgpio.gpio_write(self.h, LED_B_PIN, 0)
        self._active = False

    def cleanup(self):
        self.clear()
        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN):
            try:
                lgpio.gpio_free(self.h, pin)
            except Exception:
                pass
        try:
            lgpio.gpiochip_close(self.h)
        except Exception:
            pass
        print("🧹 RGB LED 리소스 반환 완료")
