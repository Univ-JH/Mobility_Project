import asyncio
import struct
from bleak import BleakClient, BleakScanner

# 통합 설정 파일에서 정밀 규격 변수들을 안전하게 가져옵니다.
from src.communication.comm_config import (
    BLE_DEVICE_NAME,
    STATUS_CHAR_UUID,
    EVENT_CHAR_UUID,
    COMMAND_CHAR_UUID,
    EVENT_STRUCT_FORMAT,
)

class HelmetBLEManager:
    def __init__(self):
        self.device_name  = BLE_DEVICE_NAME
        self.status_uuid  = STATUS_CHAR_UUID
        self.event_uuid   = EVENT_CHAR_UUID
        self.command_uuid = COMMAND_CHAR_UUID  # [BUG-I] Pi → Arduino write
        self.struct_format = EVENT_STRUCT_FORMAT
        
        # 메인 시스템 및 MQTT 모듈과 100% 데이터 규격을 맞춘 통합 공유 저장소
        self.last_parsed_data = {
            "seq": -1,
            "is_worn": False,
            "is_accident": False,  # 자전거 자체 충격 센서와 'OR' 연산될 핵심 변수
            "event_label": 0       # 상세 사고 종류 기록용 (1~5)
        }
        self.is_connected = False
        self.client = None
        # [CONTRACT-2] BLE 연결된 헬멧의 MAC 주소 — MQTT helmet_id 필드로 사용
        self.last_helmet_id: str = "unknown"
        # [BUG-J] 연결 상태 변경 시 호출할 async 콜백 — main.py에서 등록
        # signature: async (connected: bool, helmet_id: str) -> None
        self.on_connection_change = None

    def _status_notification_handler(self, sender, data):
        """[콜백 1] 헬멧 착용 상태 실시간 변경 수신 (1바이트 데이터)"""
        if len(data) > 0:
            status = data[0]
            is_worn = (status == 1)
            
            # 전역 데이터 상태 업데이트
            self.last_parsed_data["is_worn"] = is_worn
            
            status_text = "착용됨 (WORN)" if is_worn else "벗음 (IDLE)"
            print(f"[BLE STATUS] 헬멧 상태 변경: {status_text}")

    def _event_notification_handler(self, sender, data):
        """[콜백 2] 아두이노 바이너리 구조체 패킷 풀기 (정확히 14바이트 수신)"""
        # [FIX BUG-B] 크기 불일치 패킷 즉시 드롭 — 0패딩 파싱 시 쓰레기 데이터 ingestion 방지
        if len(data) != 14:
            print(f"⚠️ [BLE] 패킷 크기 오류: {len(data)}bytes (기대값 14bytes). 드롭.")
            return
        padded_data = data

        try:
            # 아두이노의 C++ 구조체 레이아웃 규격(<BIIIB) 그대로 언팩 수행
            schema_ver, seq, timestamp, ride_id, event_label = struct.unpack(self.struct_format, padded_data)
            
            # [판단 로직 정립] 
            # 라벨 1(전도), 2(충돌), 3(급가속), 4(급정거)가 들어오면 메인 루프가 인지하도록 사고로 판별
            # 5번(단순 이탈 의심)이나 0번(정상)일 경우는 일반 경고나 평시 상태로 분류
            is_accident = event_label in [1, 2, 3, 4]
            
            # 메인 지휘소가 읽어갈 수 있도록 딕셔너리 원자적 업데이트
            self.last_parsed_data["seq"] = seq
            self.last_parsed_data["is_accident"] = is_accident
            self.last_parsed_data["event_label"] = event_label
            
            print("-" * 50)
            print(f"[BLE EVENT] 아두이노 이벤트를 수신했습니다. (라벨: {event_label})")
            print(f"  - 이벤트 번호 : #{seq}")
            print(f"  - 구동 시간   : {timestamp / 1000.0:.2f} 초")
            print(f"  - 라이딩 ID   : {ride_id}")
            print("-" * 50)
            
        except Exception as e:
            print(f"⚠️ [BLE] 구조체 바이트 해독 에러: {e}")

    async def start_listening(self):
        """main.py의 비동기 루프 뒤에서 24시간 내내 돌며 재연결을 보장하는 감시 스레드 루프"""
        print(f"🔍 [BLE] 아두이노 헬멧 '{self.device_name}' 탐색 시퀀스 가동...")
        
        while True:
            if not self.is_connected:
                try:
                    # 필터 기반 매칭 스캔 (10초 타임아웃)
                    device = await BleakScanner.find_device_by_filter(
                        lambda d, ad: d.name and self.device_name in d.name, timeout=10.0
                    )
                    
                    if not device:
                        print(f"⚠️ [BLE] '{self.device_name}' 장치가 감지되지 않습니다. 10초 후 재탐색합니다.")
                        await asyncio.sleep(10)
                        continue

                    print(f"🌐 [BLE] 장치 포착! 핸드셰이크를 시작합니다. [맥주소: {device.address}]")

                    self.client = BleakClient(device)
                    await self.client.connect()

                    if self.client.is_connected:
                        self.is_connected = True
                        # [CONTRACT-2] 헬멧 MAC 주소 저장 — MQTT helmet_id 추적용
                        self.last_helmet_id = device.address
                        print(f"✅ [BLE] {self.device_name} 연결 성공. [helmet_id: {self.last_helmet_id}]")

                        # 아두이노의 고유 Characteristic UUID 실시간 구독 개시
                        await self.client.start_notify(self.status_uuid, self._status_notification_handler)
                        await self.client.start_notify(self.event_uuid, self._event_notification_handler)

                        # [FIX BUG-4] 연결 시점에 이미 착용 중인 경우 초기값 읽기
                        # notify는 변경 이벤트만 전달 → 연결 전 착용 상태는 수신 불가
                        try:
                            initial_status = await self.client.read_gatt_char(self.status_uuid)
                            self._status_notification_handler(None, initial_status)
                            print(f"[BLE] 초기 착용 상태 읽기 완료: {initial_status[0] if initial_status else 'N/A'}")
                        except Exception as e:
                            print(f"⚠️ [BLE] 초기 착용 상태 읽기 실패 (무시): {e}")

                        # [BUG-J] 연결 성공 콜백 — MQTT status 발행
                        if self.on_connection_change:
                            await self.on_connection_change(True, self.last_helmet_id)
                    
                except Exception as e:
                    print(f"⚠️ [BLE] 통신 레이어 초기화 실패 (재연결 대기): {e}")
                    # [FIX BUG-A] connect 성공 후 start_notify 실패 시 zombie 연결 방지
                    if self.client:
                        try:
                            await self.client.disconnect()
                        except Exception:
                            pass
                    self.is_connected = False
                    self.last_helmet_id = "unknown"
                    await asyncio.sleep(5)
                    continue
            
            # 연결 유실 감지 모니터링 파트
            if self.client and not self.client.is_connected:
                print("❌ [BLE] 아두이노 헬멧과의 연결이 유실되었습니다. 복구 모드로 진입합니다.")
                prev_helmet_id = self.last_helmet_id
                self.is_connected = False
                # 연결 끊김 시 상태 초기화 — 이전 사고 상태가 재연결 후까지 잔존하면 오작동
                self.last_parsed_data = {"seq": -1, "is_worn": False, "is_accident": False, "event_label": 0}
                self.last_helmet_id = "unknown"
                # [BUG-J] 연결 끊김 콜백 — MQTT status 발행
                if self.on_connection_change:
                    await self.on_connection_change(False, prev_helmet_id)
                
            # [FIX BUG-C] 1.0s → 0.3s: 연결 단절 감지 지연 최소화
            await asyncio.sleep(0.3)

    async def send_command(self, cmd: int) -> bool:
        """[BUG-I] Pi → Arduino 단방향 제어 명령 전송 (1 byte write).

        cmd: comm_config.CMD_* 상수 사용.
        returns: 전송 성공 여부.
        """
        if not self.is_connected or not self.client:
            return False
        try:
            await self.client.write_gatt_char(self.command_uuid, bytes([cmd]))
            return True
        except Exception as e:
            print(f"⚠️ [BLE] 명령 전송 실패 (cmd=0x{cmd:02X}): {e}")
            return False

    async def stop(self):
        """시스템 다운 시 통신 포트 및 구독 핸들러를 물리적으로 완전 반환"""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(self.status_uuid)
                await self.client.stop_notify(self.event_uuid)
                await self.client.disconnect()
            except Exception:
                pass
        self.is_connected = False
        print("🧹 [BLE] 블루투스 수신 서브시스템 안전 종료")