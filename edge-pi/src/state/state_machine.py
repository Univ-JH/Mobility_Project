import json
import time
from typing import Dict, Any, Tuple

class SafetyStateMachine:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.current_state = "NORMAL"
        self.last_evaluation_time = time.time()
        
        # 카메라 AI 신뢰도 하한선
        self.VISION_CONFIDENCE_THRESHOLD = 0.50  
        # 후방 초음파 위험 거리 (cm) - 너무 짧으면 늦으므로 50cm 유지
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
            print(f"📋 [STATE_LOG] {json.dumps(log_payload)}")
            self.current_state = new_state

    def evaluate(self, sensor_data: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        모든 센서 데이터를 취합하여 제동 레벨과 이유를 결정
        반환값: (Brake_Level, Reason, Confidence)
        """
        ble_worn = sensor_data.get("is_worn", True)
        ble_accident = sensor_data.get("is_accident", False)
        
        # 값이 안 들어왔을 때 안전을 위해 999(장애물 없음)로 처리
        sonar_dist = sensor_data.get("distance_cm", 999.0) 
        
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
        # [Priority 1] Obstacle Warning (후방 장애물 충돌 위험)
        # 초음파 에러값(0 이하) 방어 포함
        # ---------------------------------------------------------
        if 0 < sonar_dist < self.OBSTACLE_WARNING_DIST:
            reason = f"Rear obstacle too close: {sonar_dist:.1f}cm"
            self._log_state_transition("COLLISION_WARNING", reason, "level_2")
            return "level_2", reason, 1.0

        # ---------------------------------------------------------
        # [Priority 2] Fail-Safe (불확실성 제어: 카메라 가려짐 등)
        # ---------------------------------------------------------
        if vision_conf < self.VISION_CONFIDENCE_THRESHOLD:
            reason = f"Uncertain vision environment (conf: {vision_conf:.2f})"
            # 카메라가 가려졌다고 풀브레이크를 잡으면 위험하므로 가벼운 감속(level_1) 권장
            self._log_state_transition("UNCERTAIN_ENVIRONMENT", reason, "level_1")
            return "level_1", reason, vision_conf

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