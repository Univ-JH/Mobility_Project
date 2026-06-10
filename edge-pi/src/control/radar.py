import time
import threading
import smbus2

RADAR_I2C_ADDR = 0x2A

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        self._ready_at = time.time() + 2.0
        
        try:
            self.bus = smbus2.SMBus(1)
            print(f"📡 [레이더] I2C 연결 완벽 성공! (주소: 0x{RADAR_I2C_ADDR:02X})")
        except Exception as e:
            self.bus = None
            print(f"⚠️ [레이더] I2C 버스 열기 실패: {e}")

    def get_raw_status(self):
        """테스트 전용: 0x2A에서 사람 감지 데이터를 날것으로 읽어옵니다."""
        if not self.bus:
            return 0
            
        with self.lock:
            try:
                # 레이더에게 데이터 1바이트를 요구합니다.
                return self.bus.read_byte(RADAR_I2C_ADDR)
            except Exception:
                return 0

    def check_rear_approach(self):
        """메인 시스템 호출용: 사람이 감지되었는지 True/False로 반환"""
        if time.time() < self._ready_at or not self.bus:
            return False
            
        with self.lock:
            try:
                val = self.bus.read_byte(RADAR_I2C_ADDR)
                # 우선 센서가 어떤 숫자를 뱉을지 모르니, 0이 아니면 감지로 처리합니다.
                return val > 0 
            except Exception:
                return False

    def cleanup(self):
        if self.bus:
            self.bus.close()
            print("🧹 [레이더] I2C 하드웨어 리소스 안전 반환 완료")