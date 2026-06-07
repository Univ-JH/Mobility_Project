import lgpio
from .control_config import RADAR_PIN

class MmwaveRadarSensor:
    def __init__(self):
        """mmWave 센서 핀 초기화"""
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ [에러] 레이더 센서 GPIO 칩 연결 실패: {e}")
                raise e

        lgpio.gpio_claim_input(self.h, RADAR_PIN)
        print("📡 후방 mmWave 레이더 센서 모듈 준비 완료")

    def check_rear_approach(self) -> bool:
        """
        후방에 사람이나 차량이 빠른 속도로 접근 중인지 확인합니다.
        센서가 감지하면 HIGH(1)를 반환한다고 가정합니다.
        """
        try:
            return lgpio.gpio_read(self.h, RADAR_PIN) == 1
        except Exception:
            return False

    def cleanup(self):
        """안전한 리소스 반환"""
        if hasattr(self, 'h'):
            try:
                lgpio.gpio_free(self.h, RADAR_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 레이더 센서 리소스 반환 완료")
            except:
                pass
