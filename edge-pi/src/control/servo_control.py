import time
import lgpio

from .control_config import (
    SERVO_PIN, PWM_FREQ, 
    SERVO_MIN_PULSE, SERVO_MAX_PULSE, 
    BRAKE_HOLD_TIME
)

class BrakeController:
    def __init__(self):
        """컨트롤러 초기화: 라즈베리 파이 5의 GPIO 칩을 열고 핀을 준비합니다."""
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            try:
                self.h = lgpio.gpiochip_open(0)
            except Exception as e:
                print(f"⚠️ 브레이크 시스템 초기화 실패: {e}")
                raise e
        
        lgpio.gpio_claim_output(self.h, SERVO_PIN)
        
        # 시스템 켜질 때 브레이크 해제 상태로 시작
        self.release_brake()
        print("🕹️ 브레이크 컨트롤러 모듈 준비 완료")

    def _calculate_duty(self, angle):
        """내부 사용 함수: 각도를 받아 안전한 듀티 사이클(%)로 변환합니다."""
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        
        pw = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        return (pw / 20000.0) * 100.0

    def set_angle(self, angle):
        """지정된 각도로 브레이크를 조절하고, 이동 후 신호를 차단하여 모터를 보호합니다."""
        try:
            duty = self._calculate_duty(angle)
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, duty)
            
            # 테스트에서 확인한 핵심: 이동 시간 보장 후 신호 차단
            time.sleep(BRAKE_HOLD_TIME)
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
            print(f"   [Brake] {angle}도 조절 완료 (대기 모드)")
        except Exception as e:
            print(f"⚠️ 브레이크 제어 에러: {e}")

    def pull_brake(self):
        """브레이크를 완전히 잠급니다 (사고/미착용 시 호출)"""
        print("🚨 브레이크 작동!")
        self.set_angle(180)

    def release_brake(self):
        """브레이크를 완전히 풉니다 (정상 주행 시 호출)"""
        print("🟢 브레이크 해제")
        self.set_angle(0)

    def cleanup(self):
        """프로그램 종료 시 메모리와 핀을 안전하게 반환합니다."""
        try:
            lgpio.tx_pwm(self.h, SERVO_PIN, PWM_FREQ, 0)
            lgpio.gpio_free(self.h, SERVO_PIN)
            lgpio.gpiochip_close(self.h)
            print("🧹 브레이크 컨트롤러 종료 및 리소스 반환 완료")
        except:
            pass