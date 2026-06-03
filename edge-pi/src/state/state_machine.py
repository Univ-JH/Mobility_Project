import json
import time
from typing import Dict, Any, Tuple

from src.control.control_config import VISION_CONFIDENCE_THRESHOLD

class SafetyStateMachine:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.current_state = "NORMAL"
        self.last_evaluation_time = time.time()
        
        # 외부 환경 설정 파일(config)과 동기화
        self.VISION_CONFIDENCE_THRESHOLD = VISION_CONFIDENCE_THRESHOLD

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
            print(f"📋 [STATE_LOG] {json.dumps(log_payload)}")
            self.current_state = new_state

    def evaluate(self, sensor_data: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        모든 센서 데이터를 취합하여 제동 레벨과 이유를 결정
        반환값: (Brake_Level, Reason, Confidence)
        """
        ble_worn = sensor_data.get("is_worn", True)
        ble_accident = sensor_data.get("is_accident", False)
        
        vision_class = sensor_data.get("surface_class", "road")
        vision_conf = sensor_data.get("confidence", 1.0)

        # ---------------------------------------------------------
        # [Priority 0] Rider Emergency (최우선 순위: 생명 직결)
        # ---------------------------------------------------------
        if ble_accident:
            reason = "Accident/Fall detected by helmet"
            self._log_state_transition("RIDER_EMERGENCY", reason, "level_emergency")
            return "level_emergency", reason, 1.0

        if not ble_worn:
            reason = "Helmet removed during ride"
            self._log_state_transition("RIDER_EMERGENCY", reason, "level_emergency")
            return "level_emergency", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 1] Fail-Safe (불확실성 제어: 카메라 가려짐 등)
        # ---------------------------------------------------------
        if vision_conf < self.VISION_CONFIDENCE_THRESHOLD:
            reason = f"Uncertain vision environment (conf: {vision_conf:.2f})"
            self._log_state_transition("UNCERTAIN_ENVIRONMENT", reason, "level_1")
            return "level_1", reason, vision_conf

        # ---------------------------------------------------------
        # [Priority 2] Zone Violation (인도 주행 감지)
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