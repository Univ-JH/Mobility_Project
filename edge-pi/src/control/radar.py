import time
import threading
import smbus2

RADAR_I2C_ADDR = 0x2A
DETECTION_REG = 0x03  

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        self._ready_at = time.time() + 2.0
        self.consecutive_detections = 0  # 노이즈를 걸러낼 연속 감지 카운터
        
        try:
            self.bus = smbus2.SMBus(1)
            print(f"📡 [레이더] I2C 세팅 완료 (주소: 0x{RADAR_I2C_ADDR:02X}, 노이즈 방어 모드 켜짐)")
        except Exception as e:
            self.bus = None
            print(f"⚠️ [레이더] I2C 버스 열기 실패: {e}")

    def check_rear_approach(self):
        """메인 시스템 호출용: 노이즈를 걸러내고 진짜 접근일 때만 True 반환"""
        if time.time() < self._ready_at or not self.bus:
            return False
            
        with self.lock:
            try:
                val = self.bus.read_byte_data(RADAR_I2C_ADDR, DETECTION_REG)
                
                if val == 1:
                    self.consecutive_detections += 1
                else:
                    self.consecutive_detections = 0 # 한 번이라도 끊기면 카운트 초기화
                
                # 3번(약 0.3초) 연속으로 확실하게 감지되었을 때만 진짜 접근으로 인정!
                return self.consecutive_detections >= 3
                
            except Exception:
                return False

    def cleanup(self):
        if self.bus:
            self.bus.close()
            print("🧹 [레이더] I2C 하드웨어 리소스 안전 반환 완료")