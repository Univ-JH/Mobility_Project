import time
import lgpio
from .control_config import TRIG_PIN, ECHO_PIN

class UltrasonicSensor:
    def __init__(self):
        """초음파 센서 초기화 및 핀 설정"""
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ [에러] 초음파 센서 GPIO 칩 연결 실패: {e}")
                raise e

        # 핀 모드 설정
        lgpio.gpio_claim_output(self.h, TRIG_PIN)
        lgpio.gpio_claim_input(self.h, ECHO_PIN)
        
        # Trig 핀 초기화 (Low 상태 유지)
        lgpio.gpio_write(self.h, TRIG_PIN, 0)
        time.sleep(0.5) 
        
        print("📡 후방 초음파 센서 모듈 준비 완료")

    def _get_raw_distance(self):
        """단일 측정 수행 (내부 속도 최적화)"""
        try:
            lgpio.gpio_write(self.h, TRIG_PIN, 1)
            time.sleep(0.00001) # 10us 트리거
            lgpio.gpio_write(self.h, TRIG_PIN, 0)

            # 타임아웃을 30ms로 단축 (4m 거리 측정에 충분한 시간)
            pulse_start = time.time()
            timeout = pulse_start + 0.03  
            while lgpio.gpio_read(self.h, ECHO_PIN) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return float('inf')

            pulse_end = time.time()
            timeout = pulse_end + 0.03
            while lgpio.gpio_read(self.h, ECHO_PIN) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    return float('inf')

            duration = pulse_end - pulse_start
            distance = duration * 17150
            
            # 유효 범위 필터링 (2cm ~ 400cm)
            if distance < 2 or distance > 400:
                return float('inf')
                
            return round(distance, 2)

        except Exception:
            return float('inf')

    # **kwargs를 추가하여 외부에서 잡다한 인자(ride_id 등)를 보내도 에러가 나지 않음
    def get_distance(self, samples=3, **kwargs):
        """
        3번 측정하여 노이즈를 제거한 중간값을 반환합니다.
        (자전거의 실시간성을 위해 3샘플 채택)
        """
        readings = []
        for _ in range(samples):
            dist = self._get_raw_distance()
            if dist != float('inf'):
                readings.append(dist)
            time.sleep(0.01)

        if not readings:
            return float('inf')

        readings.sort()
        mid_index = len(readings) // 2
        return readings[mid_index]

    def cleanup(self):
        """안전한 리소스 반환"""
        if hasattr(self, 'h'):
            try:
                lgpio.gpio_write(self.h, TRIG_PIN, 0)
                lgpio.gpio_free(self.h, TRIG_PIN)
                lgpio.gpio_free(self.h, ECHO_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 초음파 센서 리소스 반환 완료")
            except:
                pass