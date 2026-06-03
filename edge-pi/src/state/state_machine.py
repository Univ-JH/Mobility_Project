import json
import time
from typing import Dict, Any, Tuple

from src.control.control_config import VISION_CONFIDENCE_THRESHOLD, WALK_SPEED_THRESHOLD

class SafetyStateMachine:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.current_state = "NORMAL"
        self.last_evaluation_time = time.time()
        
        self.VISION_CONFIDENCE_THRESHOLD = VISION_CONFIDENCE_THRESHOLD
        self.WALK_SPEED_THRESHOLD = WALK_SPEED_THRESHOLD

    def _log_state_transition(self, new_state: str, reason: str, action: str):
        if self.current_state != new_state:
            log_payload = {
                "eventType": "STATE_TRANSITION",
                "rideId": self.ride_id,
                "fromState": self.current_state,
                "toState": new_state,
                "actionCommand": action,
                "reason": reason
            }
            print(f"📋 [STATE_LOG] {json.dumps(log_payload)}")
            self.current_state = new_state

    def evaluate(self, sensor_data: Dict[str, Any]) -> Tuple[str, str, float]:
        ble_worn = sensor_data.get("is_worn", True)
        ble_accident = sensor_data.get("is_accident", False)
        vision_class = sensor_data.get("surface_class", "road")
        vision_conf = sensor_data.get("confidence", 1.0)
        
        # 현재 속도 가져오기 (끌바 판별용)
        speed = sensor_data.get("speed", 0.0)
        is_walking_or_stopped = (speed < self.WALK_SPEED_THRESHOLD)

        # ---------------------------------------------------------
        # [Priority 0] 물리적 사고 (속도 무관, 최우선 제동)
        # ---------------------------------------------------------
        if ble_accident:
            reason = "Accident/Fall detected by helmet or IMU"
            self._log_state_transition("RIDER_EMERGENCY", reason, "BRAKE_ENGAGE")
            return "BRAKE_ENGAGE", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 1] 헬멧 미착용
        # ---------------------------------------------------------
        if not ble_worn:
            if is_walking_or_stopped:
                # 정차 중이거나 끌고 갈 때는 헬멧을 벗어도 됨 (무시하고 패스)
                pass 
            else:
                reason = f"Helmet removed while RIDING (Speed: {speed:.1f}km/h)"
                self._log_state_transition("RIDER_EMERGENCY", reason, "BRAKE_ENGAGE")
                return "BRAKE_ENGAGE", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 2] 구역 위반 (인도 주행 - 즉각 제동)
        # ---------------------------------------------------------
        if vision_class == "sidewalk":
            if is_walking_or_stopped:
                # 자전거를 인도로 끌고 가는 것은 합법이며 안전한 행동임
                reason = f"Walking bike on sidewalk (Speed: {speed:.1f}km/h)"
                self._log_state_transition("WALK_MODE", reason, "NORMAL")
                return "NORMAL", reason, vision_conf
            else:
                # 자전거를 타고 인도를 달림 -> 즉시 브레이크 작동
                reason = f"Riding on sidewalk detected (Speed: {speed:.1f}km/h)"
                self._log_state_transition("ZONE_VIOLATION", reason, "BRAKE_ENGAGE")
                return "BRAKE_ENGAGE", reason, vision_conf

        # ---------------------------------------------------------
        # [Priority 3] Fail-Safe (비전 불확실성 - 브레이크는 잡지 않고 서버에 경고만)
        # ---------------------------------------------------------
        if vision_conf < self.VISION_CONFIDENCE_THRESHOLD:
            reason = f"Uncertain vision environment (conf: {vision_conf:.2f})"
            self._log_state_transition("UNCERTAIN_ENVIRONMENT", reason, "WARNING_ONLY")
            return "WARNING_ONLY", reason, vision_conf

        # ---------------------------------------------------------
        # [Default] 정상 주행 또는 끌바
        # ---------------------------------------------------------
        if is_walking_or_stopped:
            reason = "Safe (Walking or Stopped)"
            self._log_state_transition("WALK_MODE", reason, "NORMAL")
        else:
            reason = "Safe environment (Riding)"
            self._log_state_transition("NORMAL", reason, "NORMAL")
            
        return "NORMAL", reason, 1.0