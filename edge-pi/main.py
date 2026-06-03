import time
import asyncio
from typing import Dict, Any

# 1. 하드웨어 제어 모듈
from src.control.servo_control import BrakeController

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
        print("🚲 [시스템] 스마트 자전거 안전 시스템 (센서 최적화 모드) 초기화...")
        
        self.brake = BrakeController()
        self.ble = HelmetBLEManager()
        self.mqtt = BikeMQTTClient()
        self.vision = VisionReceiver()
        self.location = LocationMotionSensor()
        self.state_machine = SafetyStateMachine(ride_id=PI_ID)

        self.is_running = False
        
        # [데이터 통신 최적화 변수]
        self.last_telemetry_time = 0.0
        self.last_moving_state = False # 이전 주행 상태 기억 (False=정지, True=이동)

    async def _gather_sensor_data(self) -> Dict[str, Any]:
        """모든 센서 모듈에서 최신 데이터를 긁어모아 딕셔너리로 만듭니다."""
        
        helmet_data = getattr(self.ble, 'last_parsed_data', {
            "seq": -1, "is_worn": False, "is_accident": False, "event_label": 0
        }).copy()
        
        loc_data = self.location.get_sensor_data()
        
        # 이중 사고 방어망 (헬멧 사고 OR 본체 충격)
        is_accident = helmet_data.get("is_accident", False) or loc_data.get("bike_shock", False)

        return {
            "arduino_seq": helmet_data.get("seq", -1),
            "is_worn": helmet_data.get("is_worn", False),
            "is_accident": is_accident,
            "event_label": helmet_data.get("event_label", 0), 
            "surface_class": self.vision.get_surface_type(),
            "speed": loc_data.get("speed", 0.0),
            "lat": loc_data.get("lat", 0.0),
            "lon": loc_data.get("lon", 0.0),
            "bike_shock": loc_data.get("bike_shock", False)
        }

    def _execute_brake_command(self, action: str):
        """디스크 브레이크 특성에 맞춘 이진(Binary) 제어"""
        if action == "BRAKE_ENGAGE": 
            self.brake.pull_brake()  # 100% 풀브레이킹
        else: 
            self.brake.release_brake() # WARNING_ONLY나 NORMAL일 때는 브레이크 해제

    def _send_mqtt_logs(self, action: str, reason: str, sensor_data: Dict[str, Any]):
        """스마트 데이터 전송 (이벤트 발동 or 상태 변경 or 1분 경과 시에만 발송)"""
        if action == "BRAKE_ENGAGE": severity = "CRITICAL"
        elif action == "WARNING_ONLY": severity = "WARNING"
        else: severity = "NONE"

        current_time = time.time()
        
        # 1. 노이즈 필터링된 현재 이동 상태 판별 (GPS 속도 1.0km/h 기준)
        current_moving_state = sensor_data["speed"] > 1.0
        
        # 2. 전송 조건 계산
        trigger_state = (current_moving_state != self.last_moving_state) # 정지<->이동 바뀜
        trigger_event = (severity != "NONE")                             # 이벤트(경고/제동) 발생
        trigger_time  = (current_time - self.last_telemetry_time >= 60.0) # 60초(1분) 경과

        # 3. 셋 중 하나라도 만족하면 전송
        if trigger_event or trigger_state or trigger_time:
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
                brake_action=action  # ★ AWS 스키마와 완벽 매칭
            )
            # 상태 및 시간 최신화
            self.last_telemetry_time = current_time
            self.last_moving_state = current_moving_state

    async def main_loop(self):
        """시스템의 심장 역할을 하는 무한 제어 루프"""
        self.is_running = True
        
        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
        
        print("✅ [시스템] 모든 모듈 무중단 가동 완료. 안전 루프 진입.")

        EVENT_NAME_MAP = {
            1: "전도 (Fall)", 2: "충돌 (Crash)", 3: "급가속", 4: "급정거", 5: "충돌 후 이탈 의심"
        }

        try:
            while self.is_running:
                try:
                    sensor_data = await self._gather_sensor_data()

                    # [상태 판단 및 예외 처리]
                    if not self.ble.is_connected:
                        if sensor_data["is_accident"]: # 헬멧이 끊겼어도 자전거 본체가 충격을 받으면 발동
                            action, reason = "BRAKE_ENGAGE", "통신 단절 중 본체 충격 감지!"
                        else:
                            action, reason = "NORMAL", "헬멧 통신 끊김: 수동 주행 모드"
                    else:
                        action, reason, _ = self.state_machine.evaluate(sensor_data)
                        
                        # 아두이노 이벤트 디테일 덮어쓰기 로직
                        if sensor_data["is_accident"]:
                            label = sensor_data["event_label"]
                            if label in [1, 2, 3, 4]:
                                reason = f"긴급 제동 (헬멧 감지: {EVENT_NAME_MAP.get(label, '알 수 없음')})"
                            elif sensor_data["bike_shock"]:
                                reason = "긴급 제동 (자전거 본체 센서 직접 감지)"

                    # 비동기 격리 (브레이크 서보 모터)
                    await asyncio.to_thread(self._execute_brake_command, action)
                    
                    # 서버(MQTT) 전송
                    self._send_mqtt_logs(action, reason, sensor_data)

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
        
        self.location.stop()
        self.vision.stop()
        self.mqtt.stop()
        
        print("✅ [시스템] 완전히 종료되었습니다.")

if __name__ == "__main__":
    system = SmartBikeSystem()
    try:
        asyncio.run(system.main_loop())
    except KeyboardInterrupt:
        pass