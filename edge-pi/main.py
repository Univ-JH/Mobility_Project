import time
import asyncio
from typing import Dict, Any

# 1. 하드웨어 제어 모듈
from src.control.servo_control import BrakeController
from src.control.radar import MmwaveRadarSensor
from src.control.led_warning import RearApproachLED
from src.control.control_config import EMERGENCY_AUTO_RECORD

# 1-1. 카메라 녹화 모듈
from src.camera.recorder import VideoRecorder

# 2. 통신 모듈
from src.communication.ble_manager import HelmetBLEManager
from src.communication.mqtt_client import BikeMQTTClient
from src.communication.comm_config import PI_ID, BACKEND_URL, PRE_SHARED_TOKEN
from src.communication import heartbeat

# 3. 데이터 수집 모듈 (AI 비전 & GPS/IMU)
from src.ai.vision_receiver import VisionReceiver
from src.control.location import LocationMotionSensor

# 4. 상태 판단 두뇌
from src.state.state_machine import SafetyStateMachine

class SmartBikeSystem:
    def __init__(self):
        print("🚲 [시스템] 스마트 자전거 안전 시스템 (BLE 구조체 고도화 모드) 초기화...")
        
        self.brake = BrakeController()
        self.radar = MmwaveRadarSensor()
        self.led = RearApproachLED()
        self.ble = HelmetBLEManager()
        self.mqtt = BikeMQTTClient()
        self.vision = VisionReceiver()
        self.location = LocationMotionSensor()
        self.state_machine = SafetyStateMachine(ride_id=PI_ID)
        self.recorder = VideoRecorder()

        self.is_running = False
        self.last_telemetry_time = 0.0
        self._last_emergency = False  # 응급 자동 녹화 중복 방지용

    async def _gather_sensor_data(self) -> Dict[str, Any]:
        """모든 센서 모듈에서 최신 데이터를 긁어모아 딕셔너리로 만듭니다."""
        
        # 구조체 통신으로 넘어온 event_label 추가 
        helmet_data = getattr(self.ble, 'last_parsed_data', {
            "seq": -1, "is_worn": False, "is_accident": False,
            "event_label": 0, "accident_expires_at": 0.0,
        })
        loc_data = self.location.get_sensor_data()

        # [REMAIN-1] TTL 만료 체크 — Arduino는 정상 상태에서 이벤트를 보내지 않으므로
        # is_accident=True가 고착되지 않도록 accident_expires_at 이후엔 False로 취급
        helmet_is_accident = helmet_data.get("is_accident", False)
        if helmet_is_accident and time.time() > helmet_data.get("accident_expires_at", 0.0):
            helmet_is_accident = False

        # 이중 사고 방어망 (헬멧 사고 OR 본체 충격)
        is_accident = helmet_is_accident or loc_data.get("bike_shock", False)

        return {
            "arduino_seq": helmet_data.get("seq", -1),
            "is_worn": helmet_data.get("is_worn", False),
            "is_accident": is_accident,
            "event_label": helmet_data.get("event_label", 0), # 아두이노 상세 이벤트 라벨 (1~5)
            "rear_approach": self.radar.check_rear_approach(),
            "surface_class": self.vision.get_surface_type(),
            "confidence": self.vision.get_surface_confidence(),
            "speed": loc_data.get("speed", 0.0),
            "lat": loc_data.get("lat", 0.0),
            "lon": loc_data.get("lon", 0.0),
            "bike_shock": loc_data.get("bike_shock", False)
        }

    def _execute_brake_command(self, brake_level: str, current_speed: float = 0.0):
        """
        판단 결과와 현재 속도에 따라 실제 서보 모터를 움직입니다.
        (함수 호출 시 _execute_brake_command(level, speed) 형태로 속도를 넘겨주어야 합니다)
        """
        
        # 🚨 1. 생명과 직결된 긴급 상황 (헬멧 충격, 낙차 등)
        # -> 속도 상관없이 무조건 30도 풀브레이크!
        if brake_level == "level_emergency":
            self.brake.pull_brake()
            return
            
        # ⚠️ 2. 주의 및 경고 상황 (인도 진입, 카메라 가려짐, 후방 차량 접근)
        # -> 시속 5km 이상으로 달리고 있을 때만 위험하다고 판단하여 30도 브레이크 작동
        elif brake_level in ("level_1", "level_2"):
            if current_speed > 5.0:
                self.brake.pull_brake()
            else:
                # 속도가 느리면(예: 천천히 인도로 진입 중) 브레이크를 잡지 않음
                self.brake.release_brake()
                
        # 🟢 3. 정상 주행
        # -> 110도 유지
        elif brake_level == "level_0":
            self.brake.release_brake()

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

        # [REMAIN-1] MQTT 전송 간격 상한
        # 긴급 이벤트여도 최소 1초 간격 — is_accident 고착 시 0.1초 루프마다 10msg/sec 방지
        # 평시 60초 주기는 유지
        min_interval = 1.0 if is_emergency_event else 60.0
        if current_time - self.last_telemetry_time < min_interval:
            return

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

    def _on_control_command(self, action: str, payload: dict):
        """MQTT device/{id}/control 수신 핸들러 (MQTT 백그라운드 스레드에서 호출됨)."""
        if action == "start_record":
            self.recorder.start(tag="manual")
        elif action == "stop_record":
            self.recorder.stop()
        else:
            print(f"⚠️ [제어] 알 수 없는 명령: {action}")

    async def _on_helmet_connection_change(self, connected: bool, helmet_id: str):
        """[BUG-J] BLE 연결 상태 변경 → MQTT device/{id}/status 발행"""
        self.mqtt.send_helmet_status(connected=connected, helmet_id=helmet_id)

    async def main_loop(self):
        """시스템의 심장 역할을 하는 무한 제어 루프"""
        self.is_running = True

        # [BUG-J] 헬멧 연결/끊김 이벤트를 MQTT로 전달할 콜백 등록
        self.ble.on_connection_change = self._on_helmet_connection_change
        # 서버 제어 명령 수신 콜백 등록 (녹화 start/stop)
        self.mqtt.on_control_command = self._on_control_command

        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
        asyncio.create_task(heartbeat.start(BACKEND_URL, PI_ID, PRE_SHARED_TOKEN))

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

                    # 후방 고속 접근 감지 시 전방 RGB LED 빨간색 경고
                    if sensor_data.get("rear_approach"):
                        self.led.warn_rear()
                    else:
                        self.led.clear()

                    # 수동 녹화 플래그 파일 체크 (touch /tmp/record_start|stop)
                    self.recorder.check_flag_triggers()

                    # 응급 자동 녹화 (EMERGENCY_AUTO_RECORD=True 일 때만 동작)
                    is_emergency = (brake_level == "level_emergency")
                    if EMERGENCY_AUTO_RECORD:
                        if is_emergency and not self._last_emergency:
                            self.recorder.start(tag="emergency")
                        elif not is_emergency and self._last_emergency and self.recorder.is_recording:
                            self.recorder.stop()
                    self._last_emergency = is_emergency

                    # 비동기 격리 (브레이크 서보 모터)
                    await asyncio.to_thread(self._execute_brake_command, brake_level, sensor_data.get("speed", 0.0))
                    
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
            # [FIX BUG-D] async stop 호출 — ble.stop()이 async이므로 await 필요
            await self.stop()

    async def stop(self):
        print("🧹 [시스템] 안전 종료 시퀀스 가동...")
        self.is_running = False

        self.brake.release_brake()
        self.brake.cleanup()
        self.radar.cleanup()
        self.led.cleanup()
        self.recorder.cleanup()

        self.location.stop()
        self.vision.stop()
        self.mqtt.stop()
        # [FIX BUG-D] BLE 연결 정상 종료 — 기존 동기 stop()에서 누락됨
        await self.ble.stop()

        print("✅ [시스템] 완전히 종료되었습니다.")

if __name__ == "__main__":
    system = SmartBikeSystem()
    try:
        asyncio.run(system.main_loop())
    except KeyboardInterrupt:
        print("\n🛑 사용자 종료 명령(Ctrl+C) 감지. 장치를 정리합니다.")