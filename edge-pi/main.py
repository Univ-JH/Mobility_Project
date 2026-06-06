import time
import asyncio
from typing import Dict, Any

# 1. 하드웨어 제어 모듈
from src.control.servo_control import BrakeServo
from src.control.ultrasonic import UltrasonicSensor
from src.control.radar import MmwaveRadarSensor

# 2. 통신 모듈
from src.communication.ble_manager import HelmetBLEManager
from src.communication.mqtt_client import BikeMQTTClient
from src.communication.comm_config import PI_ID

# 3. 데이터 수집 모듈 (AI 비전 & GPS/IMU)
from src.vision.vision_receiver import VisionReceiver
from src.control.location import LocationMotionSensor

# 4. 상태 판단 두뇌
from src.state.state_machine import SafetyStateMachine

class SmartBikeSystem:
    def __init__(self):
        print("🚲 [시스템] 스마트 자전거 안전 시스템 (BLE 구조체 고도화 모드) 초기화...")
        
        self.brake = BrakeServo()
        self.sonar = UltrasonicSensor()
        self.radar = MmwaveRadarSensor()
        self.ble = HelmetBLEManager()
        self.mqtt = BikeMQTTClient()
        self.vision = VisionReceiver()
        self.location = LocationMotionSensor()
        self.state_machine = SafetyStateMachine(ride_id=PI_ID)

        self.is_running = False
        self.last_telemetry_time = 0.0

    async def _gather_sensor_data(self) -> Dict[str, Any]:
        """모든 센서 모듈에서 최신 데이터를 긁어모아 딕셔너리로 만듭니다."""
        
        # 구조체 통신으로 넘어온 event_label 추가 
        helmet_data = getattr(self.ble, 'last_parsed_data', {
            "seq": -1, "is_worn": False, "is_accident": False, "event_label": 0
        })
        loc_data = self.location.get_sensor_data()
        
        # 이중 사고 방어망 (헬멧 사고 OR 본체 충격)
        is_accident = helmet_data.get("is_accident", False) or loc_data.get("bike_shock", False)

        return {
            "arduino_seq": helmet_data.get("seq", -1),
            "is_worn": helmet_data.get("is_worn", False),
            "is_accident": is_accident,
            "event_label": helmet_data.get("event_label", 0), # 아두이노 상세 이벤트 라벨 (1~5)
            "distance_cm": self.sonar.get_distance(),
            "rear_approach": self.radar.check_rear_approach(),
            "surface_class": self.vision.get_surface_type(),
            "confidence": self.vision.get_surface_confidence(),
            "speed": loc_data.get("speed", 0.0),
            "lat": loc_data.get("lat", 0.0),
            "lon": loc_data.get("lon", 0.0),
            "bike_shock": loc_data.get("bike_shock", False)
        }

    def _execute_brake_command(self, brake_level: str):
        """판단 결과에 따라 실제 서보 모터를 움직입니다."""
        if brake_level == "level_emergency": self.brake.pull_brake(power=100)
        elif brake_level == "level_2": self.brake.pull_brake(power=60)
        elif brake_level == "level_1": self.brake.pull_brake(power=30)
        elif brake_level == "level_0": self.brake.release_brake()

    def _send_mqtt_logs(self, brake_level: str, reason: str, sensor_data: Dict[str, Any]):
        """NoSQL DB에 최적화된 단일 JSON 패킷 전송을 수행합니다."""

        if brake_level == "level_emergency": severity = "CRITICAL"
        elif brake_level == "level_2": severity = "WARNING"
        elif brake_level == "level_1": severity = "INFO"
        else: severity = "NONE"

        # [CONTRACT-3] event_label 기반 사고 판단 신뢰도 계산
        # 충돌(4G 이상 물리 임팩트): 가장 명확한 물리 신호 → 0.95
        # 전도(1.5초 지속 기울기): 유지 시간으로 확증 → 0.85
        # 충돌 후 이탈(label 5): 복합 조건 충족 → 0.80
        # 급가속/급정거(label 3/4): 정방향 축 임계값, 오감지 여지 있음 → 0.75
        # 자전거 본체 충격만(BLE 사고 없음): Pi IMU 단독 판단 → 0.70
        # 평시: 기준값 → 0.50
        _LABEL_CONFIDENCE = {1: 0.85, 2: 0.95, 3: 0.75, 4: 0.75, 5: 0.80}
        label = sensor_data.get("event_label", 0)
        if label in _LABEL_CONFIDENCE:
            confidence = _LABEL_CONFIDENCE[label]
        elif sensor_data.get("bike_shock", False):
            confidence = 0.70
        else:
            confidence = 0.50

        current_time = time.time()

        # 이벤트(사고 감지, 아두이노 특별 이벤트) 또는 위험(브레이크 개입) 상황 판단
        is_emergency_event = (
            severity != "NONE" or
            sensor_data.get("is_accident", False) or
            sensor_data.get("event_label", 0) != 0
        )

        # 이벤트 발생 시 즉시 전송, 평시에는 60초 대기 (1분 주기)
        if is_emergency_event or (current_time - self.last_telemetry_time >= 60.0):
            self.mqtt.send_bike_state(
                speed=sensor_data["speed"],
                road_type=sensor_data["surface_class"],
                lat=sensor_data["lat"],
                lon=sensor_data["lon"],
                arduino_seq=sensor_data["arduino_seq"],
                is_worn=sensor_data["is_worn"],
                is_accident=sensor_data["is_accident"],
                severity=severity,
                reason=reason,
                brake_level=brake_level,
                confidence=confidence,
                battery_level=-1,
                helmet_id=self.ble.last_helmet_id,
            )
            self.last_telemetry_time = current_time

    async def main_loop(self):
        """시스템의 심장 역할을 하는 무한 제어 루프"""
        self.is_running = True
        
        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
        
        print("✅ [시스템] 모든 모듈 무중단 가동 완료. 안전 루프 진입.")

        # 아두이노 C++ 이벤트 라벨 매핑 딕셔너리
        EVENT_NAME_MAP = {
            1: "전도 (Fall)",
            2: "충돌 (Crash)",
            3: "급가속",
            4: "급정거",
            5: "충돌 후 이탈 의심 (Crash to Idle)"
        }

        try:
            while self.is_running:
                try:
                    sensor_data = await self._gather_sensor_data()

                    # [상태 판단 및 예외 처리]
                    if not self.ble.is_connected:
                        if sensor_data["is_accident"]: # 헬멧이 끊겼어도 자전거 본체가 충격을 받으면 발동
                            brake_level, reason = "level_emergency", "통신 단절 중 본체 충격 감지!"
                        else:
                            brake_level, reason = "level_0", "헬멧 통신 끊김: 수동 주행 모드"
                    else:
                        brake_level, reason, _ = self.state_machine.evaluate(sensor_data)
                        
                        # 아두이노 이벤트 디테일 덮어쓰기 로직
                        # 사고가 발생했을 때, 그 원인이 헬멧이라면 정확한 원인을 AWS로 보냄
                        if sensor_data["is_accident"]:
                            label = sensor_data["event_label"]
                            if label in [1, 2, 3, 4]:
                                reason = f"긴급 제동 (헬멧 감지: {EVENT_NAME_MAP[label]})"
                            elif sensor_data["bike_shock"]:
                                reason = "긴급 제동 (자전거 본체 센서 직접 감지)"

                    # 후방 고속 접근 감지 시 부저 알림
                    if sensor_data.get("rear_approach"):
                        self.radar.trigger_warning()

                    # 비동기 격리 (브레이크 서보 모터)
                    await asyncio.to_thread(self._execute_brake_command, brake_level)
                    
                    # 서버(MQTT) 전송
                    self._send_mqtt_logs(brake_level, reason, sensor_data)

                except Exception as e:
                    print(f"⚠️ [시스템 에러] 루프 1회 스킵 (복구 중): {e}")
                    await asyncio.sleep(0.5)
                    continue

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("🛑 [시스템] 루프 강제 취소됨.")
        finally:
            self.stop()

    def stop(self):
        print("🧹 [시스템] 안전 종료 시퀀스 가동...")
        self.is_running = False
        
        self.brake.release_brake() 
        self.brake.cleanup()
        self.sonar.cleanup()
        self.radar.cleanup()
        
        self.location.stop()
        self.vision.stop()
        self.mqtt.stop()
        
        print("✅ [시스템] 완전히 종료되었습니다.")

if __name__ == "__main__":
    system = SmartBikeSystem()
    try:
        asyncio.run(system.main_loop())
    except KeyboardInterrupt:
        print("\n🛑 사용자 종료 명령(Ctrl+C) 감지. 장치를 정리합니다.")