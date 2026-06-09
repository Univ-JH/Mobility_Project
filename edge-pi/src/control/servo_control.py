import time
import lgpio
import threading   # 스레드 락을 위한 모듈 추가
from .control_config import (
    SERVO_PIN, PWM_FREQ, 
    SERVO_MIN_PULSE, SERVO_MAX_PULSE, 
    BRAKE_HOLD_TIME,
    BRAKE_RELEASE_ANGLE,
    BRAKE_PULL_ANGLE
)

class BrakeController:
    def __init__(self):
        self.current_angle = None  # 현재 각도 추적용 변수
        self.lock = threading.Lock()  # 자물쇠(락) 생성

        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ [에러] 브레이크 시스템 GPIO 칩을 열 수 없습니다: {e}")
                raise e
        
        try:
            lgpio.gpio_claim_output(self.h, SERVO_PIN)
        except Exception as e:
            print(f"⚠️ [에러] {SERVO_PIN}번 핀을 사용할 수 없습니다: {e}")
            raise e
        
        # 초기화 시 자전거 주행 각도(110도)로 안전하게 시작
        self.release_brake()
        print("🕹️ 브레이크 컨트롤러 모듈 준비 완료")

    def _calculate_duty(self, angle):
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        pw = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        return (pw / 20000.0) * 100.0

    def set_angle(self, angle):
        """지정된 각도로 회전 명령을 내린 후, 물리적 도달 여부와 관계없이 1초 후 동력을 강제 차단합니다.(스레드 충돌 방지 락 적용)"""
        if self.current_angle == angle:
            return
        
        # 자물쇠로 잠그기: 다른 명령이 실행 중이면 끝날 때까지 대기하거나 무시
        with self.lock:
            # 락을 얻고 들어왔는데 그새 각도가 바뀌었을 수 있으므로 이중 체크
            if self.current_angle == angle:
                return

        try:
            duty = self._calculate_duty(angle)
            
            # 1. 서보 모터에 PWM 신호를 주어 회전을 시작합니다.
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, duty)
            self.current_angle = angle  
            
            # 2. 물리적 차단 타이머 작동 (지정된 1.0초 동안 모터가 해당 위치를 강하게 유지합니다.)
            time.sleep(BRAKE_HOLD_TIME) 
            
            # 3. [이중 안전장치] 1초 경과 후 PWM 신호를 완전히 종료하고 핀 출력을 LOW(0)로 만듭니다.
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
            lgpio.gpio_write(self.h, SERVO_PIN, 0)
            
            print(f"   [Brake] {angle}도 제어 시도 후 {BRAKE_HOLD_TIME}초 경과 -> 모터 내부 동력 해제 완료")
            
        except Exception as e:
            print(f"⚠️ 브레이크 제어 동작 중 에러 발생: {e}")

    def pull_brake(self):
        """브레이크 완전 작동 (지정된 30도로 이동)"""
        if self.current_angle != BRAKE_PULL_ANGLE:
            print(f"🚨 [명령] 브레이크 작동! ({BRAKE_PULL_ANGLE}도 제동 위치로 이동)")
            self.set_angle(BRAKE_PULL_ANGLE)

    def release_brake(self):
        """브레이크 완전 해제 (지정된 110도 정상 주행 위치로 이동)"""
        if self.current_angle != BRAKE_RELEASE_ANGLE:
            print(f"🟢 [명령] 브레이크 해제 ({BRAKE_RELEASE_ANGLE}도 주행 위치로 이동)")
            self.set_angle(BRAKE_RELEASE_ANGLE)

    def cleanup(self):
        """자원 해제 방어 로직"""
        if hasattr(self, 'h'):
            try:
                lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
                lgpio.gpio_write(self.h, SERVO_PIN, 0)
                lgpio.gpio_free(self.h, SERVO_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 브레이크 리소스 안전 반환 완료")
            except Exception as e:
                pass