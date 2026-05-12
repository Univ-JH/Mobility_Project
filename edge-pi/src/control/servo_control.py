import time
import lgpio
from .control_config import (
    SERVO_PIN, PWM_FREQ, 
    SERVO_MIN_PULSE, SERVO_MAX_PULSE, 
    BRAKE_HOLD_TIME
)

class BrakeController:
    def __init__(self):
        self.current_angle = None  # 현재 각도 추적용 변수 추가
        
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
            print(f"⚠️ [에러] {SERVO_PIN}번 핀을 사용할 수 없습니다. (다른 프로세스가 사용 중일 수 있음): {e}")
            raise e
        
        # 초기화 시 브레이크를 해제 상태로 맞춤
        self.release_brake()
        print("🕹️ 브레이크 컨트롤러 모듈 준비 완료")

    def _calculate_duty(self, angle):
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        pw = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        return (pw / 20000.0) * 100.0

    def set_angle(self, angle):
        """지정된 각도로 이동 후 신호를 차단합니다."""
        # 방어 로직: 이미 해당 각도에 도달해 있다면 중복 실행하지 않음
        if self.current_angle == angle:
            return

        try:
            duty = self._calculate_duty(angle)
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, duty)
            self.current_angle = angle  # 현재 상태 업데이트
            
            # 주의: 여기서 1초간 멈추므로 통합 시 비동기(async) 처리가 필요할 수 있습니다.
            time.sleep(BRAKE_HOLD_TIME) 
            
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
            print(f"   [Brake] {angle}도 조절 완료 및 신호 차단")
            
        except Exception as e:
            print(f"⚠️ 브레이크 제어 동작 중 에러 발생: {e}")

    def pull_brake(self):
        """브레이크 완전 작동 (사고/미착용 시)"""
        # 중복 메시지 출력을 막기 위해 각도 체크
        if self.current_angle != 180:
            print("🚨 [명령] 브레이크 작동!")
            self.set_angle(180)

    def release_brake(self):
        """브레이크 완전 해제 (정상 주행 시)"""
        if self.current_angle != 0:
            print("🟢 [명령] 브레이크 해제")
            self.set_angle(0)

    def cleanup(self):
        """자원 해제 방어 로직 강화"""
        if hasattr(self, 'h'): # h 객체가 정상적으로 생성되었을 때만 해제 시도
            try:
                lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
                lgpio.gpio_free(self.h, SERVO_PIN)
                lgpio.gpiochip_close(self.h)
                print("🧹 브레이크 리소스 안전 반환 완료")
            except Exception as e:
                print(f"⚠️ 리소스 반환 중 에러 (무시 가능): {e}")