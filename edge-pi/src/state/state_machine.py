# src/state/state_machine.py
import json
import time
from typing import Dict, Any, Tuple

class SafetyStateMachine:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.current_state = "NORMAL"
        self.last_evaluation_time = time.time()
        
        # 카메라 AI 신뢰도 하한선 (Fail-Safe 기준점)
        self.VISION_CONFIDENCE_THRESHOLD = 0.50  
        # 초음파 위험 거리 (cm)
        self.OBSTACLE_WARNING_DIST = 50.0        

    def _log_state_transition(self, new_state: str, reason: str, level: str):
        """[RULE: 구조화된 로깅] 상태 전이 시 기록"""
        if self.current_state != new_state:
            log_payload = {
                "eventType": "STATE_TRANSITION",
                "rideId": self.ride_id,
                "fromState": self.current_state,
                "toState": new_state,
                "brakeCommand": level,
                "reason": reason
            }
            print(f"[JSON_LOG] {json.dumps(log_payload)}")
            self.current_state = new_state

    def evaluate(self, sensor_data: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        모든 센서 데이터를 취합하여 제동 레벨과 이유를 결정
        반환값: (Brake_Level, Reason, Confidence)
        """
        # 1. 데이터 추출 (없을 경우를 대비한 안전한 기본값 설정)
        ble_worn = sensor_data.get("is_worn", True)
        ble_accident = sensor_data.get("is_accident", False)
        
        sonar_dist = sensor_data.get("distance_cm", 999.0)
        
        vision_class = sensor_data.get("surface_class", "road")
        vision_conf = sensor_data.get("confidence", 1.0)

        # ---------------------------------------------------------
        # [Priority 0] Fail-Safe (불확실성 제어: 보이지 않으면 멈춘다)
        # ---------------------------------------------------------
        if vision_conf < self.VISION_CONFIDENCE_THRESHOLD:
            reason = f"Uncertain vision environment (conf: {vision_conf:.2f})"
            self._log_state_transition("UNCERTAIN_ENVIRONMENT", reason, "level_2")
            return "level_2", reason, vision_conf

        if sonar_dist <= 0 or sonar_dist > 400: # 비정상(먹통) 값
            reason = "Ultrasonic sensor failure or out of range"
            self._log_state_transition("SENSOR_FAULT", reason, "level_2")
            return "level_2", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 1] Rider Emergency (헬멧 응급 상황)
        # ---------------------------------------------------------
        if not ble_worn:
            reason = "Helmet removed during ride"
            self._log_state_transition("RIDER_EMERGENCY", reason, "level_emergency")
            return "level_emergency", reason, 1.0
            
        if ble_accident:
            reason = "Accident/Fall detected by helmet"
            self._log_state_transition("RIDER_EMERGENCY", reason, "level_emergency")
            return "level_emergency", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 2] Obstacle Warning (전방 장애물 충돌 위험)
        # ---------------------------------------------------------
        if sonar_dist < self.OBSTACLE_WARNING_DIST:
            reason = f"Obstacle too close: {sonar_dist:.1f}cm"
            self._log_state_transition("COLLISION_WARNING", reason, "level_2")
            return "level_2", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 3] Zone Violation (인도 주행 감지)
        # ---------------------------------------------------------
        if vision_class == "sidewalk":
            reason = f"Sidewalk riding detected (conf: {vision_conf:.2f})"
            self._log_state_transition("ZONE_VIOLATION", reason, "level_1")
            return "level_1", reason, vision_conf

        # ---------------------------------------------------------
        # [Default] Normal (정상 주행)
        # ---------------------------------------------------------
        reason = "Safe environment"
        self._log_state_transition("NORMAL", reason, "level_0")
        return "level_0", reason, 1.0