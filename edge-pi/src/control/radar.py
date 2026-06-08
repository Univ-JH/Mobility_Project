import time
import lgpio
from .control_config import RADAR_CR_PIN, RADAR_DT_PIN

_WARMUP_SEC = 2.0  # 레이더 초기화 시 HIGH 오출력 방지


class MmwaveRadarSensor:
    def __init__(self):
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ [에러] 레이더 센서 GPIO 칩 연결 실패: {e}")
                raise e

        lgpio.gpio_claim_input(self.h, RADAR_CR_PIN, lgpio.SET_PULL_DOWN)
        lgpio.gpio_claim_input(self.h, RADAR_DT_PIN, lgpio.SET_PULL_DOWN)
        self._ready_at = time.time() + _WARMUP_SEC
        print("📡 후방 mmWave 레이더 센서 모듈 준비 완료")

    def check_rear_approach(self) -> bool:
        """CR(근거리) 또는 DT(원거리) 중 하나라도 HIGH면 접근 감지."""
        if time.time() < self._ready_at:
            return False  # warm-up 중 오감지 차단
        try:
            cr = lgpio.gpio_read(self.h, RADAR_CR_PIN) == 1
            dt = lgpio.gpio_read(self.h, RADAR_DT_PIN) == 1
            return cr or dt
        except Exception:
            return False

    def cleanup(self):
        if hasattr(self, 'h'):
            try:
                lgpio.gpio_free(self.h, RADAR_CR_PIN)
                lgpio.gpio_free(self.h, RADAR_DT_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 레이더 센서 리소스 반환 완료")
            except Exception:
                pass
