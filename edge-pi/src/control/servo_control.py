# sudo pigpiod
import time
import json
import pigpio
from typing import Dict, Any

from .control_config import (
    SERVO_PIN, SERVO_MIN_PULSE, SERVO_MAX_PULSE, BRAKE_LEVELS
)

class BrakeController:
    def __init__(self, ride_id: str = "SYSTEM_TEST"):
        """서보 모터 초기화 및 기본 상태(해제) 설정"""
        self.ride_id = ride_id
        
        # [RULE: Fail-Safe] pigpio 데몬 연결 확인
        self.pi = pigpio.pi()
        if not self.pi.connected:
            self._log_action("SYSTEM_FAULT", "Failed to connect to pigpio daemon. (Run 'sudo pigpiod')", "HIGH")
            raise RuntimeError("pigpio 데몬에 연결할 수 없습니다. 터미널에서 'sudo pigpiod'를 실행하세요.")

        # 초기 상태: 브레이크 해제
        self.current_level = "level_0"
        self._set_angle(BRAKE_LEVELS[self.current_level])
        print(f"[SERVO_INIT] 브레이크 컨트롤러 초기화 완료 (현재: {self.current_level})")

    def _set_angle(self, angle: int):
        """내부 유틸: 각도(0~180)를 펄스폭으로 변환하여 모터에 명령 전달"""
        # 안전을 위해 각도 제한
        angle = max(0, min(180, angle))
        
        # 0~180도를 500~2500us 펄스폭으로 매핑
        pulse_width = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        
        # 하드웨어 PWM 신호 전송
        self.pi.set_servo_pulsewidth(SERVO_PIN, int(pulse_width))

    def _log_action(self, event_type: str, reason: str, severity: str, confidence: float = 1.0):
        """[RULE: 관측성] 제어 로그 기록"""
        log_payload = {
            "eventType": event_type,
            "rideId": self.ride_id,
            "severity": severity,
            "reason": reason,
            "confidence": confidence
        }
        print(f"[JSON_LOG] {json.dumps(log_payload)}")

    def execute_brake(self, level: str, reason: str, confidence: float = 1.0):
        """
        [외부 인터페이스] 요청된 제동 레벨로 브레이크를 작동시킵니다.
        
        Args:
            level (str): "level_0", "level_1", "level_2", "level_emergency"
            reason (str): 브레이크를 잡는 이유 (예: "장애물 감지", "헬멧 전도")
            confidence (float): 판단의 신뢰도 (0.0 ~ 1.0)
        """
        if level not in BRAKE_LEVELS:
            self._log_action("INVALID_COMMAND", f"Unsupported brake level: {level}", "WARNING")
            return

        # 중복 명령 무시 (이미 같은 레벨이면 모터를 다시 건드리지 않음)
        if level == self.current_level:
            return

        target_angle = BRAKE_LEVELS[level]
        self._set_angle(target_angle)
        self.current_level = level

        # 심각도 결정 (레벨에 따라)
        severity = "HIGH" if "emergency" in level else "INFO"
        
        # [RULE: 이유 있는 제어] 기록
        action_msg = f"Brake set to {level} ({target_angle} deg) due to: {reason}"
        self._log_action("BRAKE_ENGAGED", action_msg, severity, confidence)

    def release_brake(self, reason: str = "Safe condition restored"):
        """브레이크를 완전히 해제합니다."""
        self.execute_brake("level_0", reason)

    def cleanup(self):
        """프로그램 종료 시 서보 모터 전원 차단 (펄스폭 0 = 정지)"""
        if self.pi.connected:
            self.release_brake("System shutdown")
            time.sleep(0.5) # 해제 각도로 돌아갈 시간 확보
            self.pi.set_servo_pulsewidth(SERVO_PIN, 0)
            self.pi.stop()
            print("[SERVO_CLEANUP] 서보 모터 제어 종료.")