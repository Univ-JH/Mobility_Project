import time
import lgpio
import threading
from .control_config import RADAR_PIN, BUZZER_PIN

class MmwaveRadarSensor:
    def __init__(self):
        """mmWave 센서 및 부저 핀 초기화"""
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ [에러] 레이더 센서 GPIO 칩 연결 실패: {e}")
                raise e

        # 핀 모드 설정
        lgpio.gpio_claim_input(self.h, RADAR_PIN)
        lgpio.gpio_claim_output(self.h, BUZZER_PIN)
        
        # 부저 초기화 (소리 끔)
        lgpio.gpio_write(self.h, BUZZER_PIN, 0)
        
        self.is_buzzing = False
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

    def _beep_routine(self):
        """메인 루프를 방해하지 않도록 별도 스레드에서 삑-삑- 소리를 냅니다."""
        try:
            for _ in range(3):
                lgpio.gpio_write(self.h, BUZZER_PIN, 1)
                time.sleep(0.1)
                lgpio.gpio_write(self.h, BUZZER_PIN, 0)
                time.sleep(0.1)
        except Exception:
            pass
        finally:
            self.is_buzzing = False

    def trigger_warning(self):
        """후방 감지 시 부저를 울립니다. 이미 울리고 있다면 무시합니다."""
        if not self.is_buzzing:
            self.is_buzzing = True
            threading.Thread(target=self._beep_routine, daemon=True).start()

    def cleanup(self):
        """안전한 리소스 반환"""
        if hasattr(self, 'h'):
            try:
                lgpio.gpio_write(self.h, BUZZER_PIN, 0)
                lgpio.gpio_free(self.h, RADAR_PIN)
                lgpio.gpio_free(self.h, BUZZER_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 레이더 센서 리소스 반환 완료")
            except:
                pass
