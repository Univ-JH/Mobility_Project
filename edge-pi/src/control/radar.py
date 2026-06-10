import time
import threading
import smbus2

# 스캐너가 찾아낸 우리 레이더 센서의 I2C 고유 주소!
RADAR_I2C_ADDR = 0x36

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        self._ready_at = time.time() + 2.0
        
        try:
            self.bus = smbus2.SMBus(1)
            print(f"📡 [레이더] I2C 모드 연결 성공! (주소: 0x{RADAR_I2C_ADDR:02X})")
        except Exception as e:
            self.bus = None
            print(f"⚠️ [레이더] I2C 버스 열기 실패: {e}")

    def get_raw_status(self):
        """테스트 전용: I2C로 넘어오는 날것의 데이터를 확인합니다."""
        if not self.bus:
            return 0
            
        with self.lock:
            try:
                # 0x36 주소에서 기본 상태 바이트를 읽어옵니다.
                return self.bus.read_byte(RADAR_I2C_ADDR)
            except Exception:
                return 0

    def check_rear_approach(self):
        """메인 시스템 호출용: 사람이 감지되었는지 확인"""
        if time.time() < self._ready_at or not self.bus:
            return False
            
        with self.lock:
            try:
                val = self.bus.read_byte(RADAR_I2C_ADDR)
                # 센서 주변에 사람이 없으면 0, 감지되면 0보다 큰 숫자(보통 1, 255 등)가 나옵니다.
                return val > 0 
            except Exception:
                return False

    def cleanup(self):
        if self.bus:
            self.bus.close()
            print("🧹 [레이더] I2C 하드웨어 리소스 안전 반환 완료")