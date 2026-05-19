import time
import asyncio
from typing import Dict, Any

# 1. 하드웨어 제어 모듈
from src.control.servo_control import BrakeServo
from src.control.ultrasonic import UltrasonicSensor

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
        print("🚲 [시스템] 스마트 자전거 안전 시스템 (통합 24/7 모드) 초기화...")
        
        self.brake = BrakeServo()
        self.sonar = UltrasonicSensor()
        self.ble = HelmetBLEManager()
        self.mqtt = BikeMQTTClient()
        self.vision = VisionReceiver()
        self.location = LocationMotionSensor()
        self.state_machine = SafetyStateMachine(ride_id=PI_ID)

        self.is_running = False
        self.last_telemetry_time = 0.0

    async def _gather_sensor_data(self) -> Dict[str, Any]:
        """모든 센서 모듈에서 최신 데이터를 긁어모아 딕셔너리로 만듭니다."""
        
        # BLE 데이터 안전 추출 (데이터가 아직 안 왔을 경우를 대비한 기본값)
        helmet_data = getattr(self.ble, 'last_parsed_data', {
            "seq": -1, "is_worn": False, "is_accident": False
        })
        loc_data = self.location.get_sensor_data()
        
        # [핵심] 이중 사고 방어망 (OR 연산)
        # 헬멧에서 사고를 감지하거나, 자전거 본체(IMU)가 충격을 받으면 모두 사고로 간주
        is_accident = helmet_data.get("is_accident", False) or loc_data.get("bike_shock", False)

        return {
            "arduino_seq": helmet_data.get("seq", -1),
            "is_worn": helmet_data.get("is_worn", False),
            "is_accident": is_accident,
            "distance_cm": self.sonar.get_distance(),
            "surface_class": self.vision.get_surface_type(),
            "speed": loc_data.get("speed", 0.0),
            "lat": loc_data.get("lat", 0.0),
            "lon": loc_data.get("lon", 0.0)
        }

    def _execute_brake_command(self, brake_level: str):
        """판단 결과에 따라 실제 서보 모터를 움직입니다."""
        if brake_level == "level_emergency": self.brake.pull_brake(power=100)
        elif brake_level == "level_2": self.brake.pull_brake(power=60)
        elif brake_level == "level_1": self.brake.pull_brake(power=30)
        elif brake_level == "level_0": self.brake.release_brake()

    def _send_mqtt_logs(self, brake_level: str, reason: str, sensor_data: Dict[str, Any]):
        """NoSQL DB에 최적화된 단일 JSON 패킷 전송을 수행합니다."""
        
        # 브레이크 강도에 따른 위험도(Severity) 가중치 자동 매핑
        if brake_level == "level_emergency": severity = "CRITICAL"
        elif brake_level == "level_2": severity = "WARNING"
        elif brake_level == "level_1": severity = "INFO"
        else: severity = "NONE"

        current_time = time.time()
        
        # [데이터 스로틀링 로직]
        # 사고나 브레이크 개입(NONE이 아님)이 발생하면 즉시 전송!
        # 정상 주행 중일 때는 2초에 한 번만 전송하여 서버 과부하 방지
        if severity != "NONE" or (current_time - self.last_telemetry_time >= 2.0):
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
                brake_level=brake_level
            )
            self.last_telemetry_time = current_time

    async def main_loop(self):
        """시스템의 심장 역할을 하는 무한 제어 루프"""
        self.is_running = True
        
        # 백그라운드 모듈 가동
        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
        
        print("✅ [시스템] 모든 모듈 무중단 가동 완료. 안전 루프 진입.")

        try:
            while self.is_running:
                try:
                    sensor_data = await self._gather_sensor_data()

                    # [페일 세이프 방어] 헬멧 통신이 끊겼을 때의 처리
                    if not self.ble.is_connected:
                        if sensor_data["is_accident"]:
                            # 블루투스가 끊겨도 본체 센서가 충격을 잡으면 긴급 제동
                            brake_level, reason = "level_emergency", "통신 단절 중 본체 충격 감지!"
                        else:
                            # 평상시 끊기면 브레이크를 풀고 수동 주행 허용
                            brake_level, reason = "level_0", "헬멧 통신 끊김: 수동 주행 모드"
                    else:
                        # 통신이 정상이면 State Machine에 판단을 맡김
                        brake_level, reason, _ = self.state_machine.evaluate(sensor_data)

                    # [비동기 격리] 브레이크 모터 동작(sleep)이 통신을 막지 않도록 별도 스레드에서 실행
                    await asyncio.to_thread(self._execute_brake_command, brake_level)
                    
                    # 통합된 MQTT 전송 실행
                    self._send_mqtt_logs(brake_level, reason, sensor_data)

                except Exception as e:
                    # 초음파 튐, 포트 에러 등 일시적 오류 발생 시 시스템 사망 방지
                    print(f"⚠️ [시스템 에러] 루프 1회 스킵 (복구 중): {e}")
                    await asyncio.sleep(0.5)
                    continue

                # 루프 사이클: 10Hz 유지 (0.1초)
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("🛑 [시스템] 루프 강제 취소됨.")
        finally:
            self.stop()

    def stop(self):
        print("🧹 [시스템] 안전 종료 시퀀스 가동...")
        self.is_running = False
        
        self.brake.release_brake() # 종료 시 브레이크 락 해제
        self.brake.cleanup()
        self.sonar.cleanup()
        
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