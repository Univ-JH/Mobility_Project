import time
import threading
import smbus2

RADAR_I2C_ADDR = 0x2A
DETECTION_REG = 0x03  # 우리가 스캐너로 찾아낸 진짜 사람 감지 방 번호!

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        self._ready_at = time.time() + 2.0
        
        try:
            self.bus = smbus2.SMBus(1)
            print(f"📡 [레이더] I2C 최종 세팅 완료! (주소: 0x{RADAR_I2C_ADDR:02X}, 감지방: 0x{DETECTION_REG:02X})")
        except Exception as e:
            self.bus = None
            print(f"⚠️ [레이더] I2C 버스 열기 실패: {e}")

    def check_rear_approach(self):
        """메인 시스템 호출용: 사람이 감지되었는지 True/False로 반환"""
        if time.time() < self._ready_at or not self.bus:
            return False
            
        with self.lock:
            try:
                # 0x2A 주소의 호텔에서, 0x03번 방의 데이터만 정확히 빼옵니다.
                val = self.bus.read_byte_data(RADAR_I2C_ADDR, DETECTION_REG)
                
                # 로그에서 확인했듯, 값이 1이면 감지된 것입니다.
                return val == 1
            except Exception:
                return False

    def cleanup(self):
        if self.bus:
            self.bus.close()
            print("🧹 [레이더] I2C 하드웨어 리소스 안전 반환 완료")