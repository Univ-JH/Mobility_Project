import asyncio
import struct
from bleak import BleakClient, BleakScanner

# 통합 설정 파일에서 정밀 규격 변수들을 안전하게 가져옵니다.
from src.communication.comm_config import (
    BLE_DEVICE_NAME, 
    STATUS_CHAR_UUID, 
    EVENT_CHAR_UUID, 
    EVENT_STRUCT_FORMAT
)

class HelmetBLEManager:
    def __init__(self):
        self.device_name = BLE_DEVICE_NAME
        self.status_uuid = STATUS_CHAR_UUID
        self.event_uuid = EVENT_CHAR_UUID
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
        # 데이터가 잘리거나 쓰레기 값이 붙어 들어왔을 때를 대비한 패딩 방어선
        if len(data) < 14:
            padded_data = data + b'\x00' * (14 - len(data))
        else:
            padded_data = data[:14]

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
                        print(f"✅ [BLE] {self.device_name} 무선 통신망 연결 성공. 센서 알림(Notify)을 개방합니다.")
                        
                        # 아두이노의 고유 Characteristic UUID 실시간 구독 개시
                        await self.client.start_notify(self.status_uuid, self._status_notification_handler)
                        await self.client.start_notify(self.event_uuid, self._event_notification_handler)
                    
                except Exception as e:
                    print(f"⚠️ [BLE] 통신 레이어 초기화 실패 (재연결 대기): {e}")
                    self.is_connected = False
                    await asyncio.sleep(5)
                    continue
            
            # 연결 유실 감지 모니터링 파트
            if self.client and not self.client.is_connected:
                print("❌ [BLE] 아두이노 헬멧과의 연결이 유실되었습니다. 복구 모드로 진입합니다.")
                self.is_connected = False
                
            await asyncio.sleep(1.0)

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