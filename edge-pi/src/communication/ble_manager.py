import asyncio
from bleak import BleakClient, BleakScanner
from .comm_config import TARGET_DEVICE_NAME, RX_CHARACTERISTIC_UUID

class HelmetBLEManager:
    def __init__(self):
        self.device_name = TARGET_DEVICE_NAME
        self.char_uuid = RX_CHARACTERISTIC_UUID
        self.is_connected = False
        self.on_data_received = None 
        
        # 비정상 끊김을 즉각 감지하기 위한 이벤트 객체
        self._disconnect_event = asyncio.Event() 

    def _disconnect_callback(self, client):
        """블루투스 기기와 연결이 끊어지면 즉시 호출되는 시스템 콜백"""
        print("\n❌ [BLE] 헬멧과의 연결이 끊어졌습니다! (재연결 대기)")
        self.is_connected = False
        self._disconnect_event.set() # 끊김 이벤트 발생!

    def _parse_data(self, raw_text):
        """외계어 데이터를 안전하게 딕셔너리로 파싱 (방어 로직 강화)"""
        parsed_data = {"is_worn": True, "is_accident": False, "speed": 0.0}
        try:
            parts = raw_text.split(',')
            for part in parts:
                if ':' not in part: continue
                key, value = part.split(':')
                
                if key == 'W':
                    parsed_data["is_worn"] = (value == '1')
                elif key == 'A':
                    parsed_data["is_accident"] = (value == '1')
                elif key == 'S':
                    # 값이 이상하게 와도(예: "20.5a") 프로그램이 죽지 않도록 방어
                    parsed_data["speed"] = float(value.replace(filter(lambda x: not x.isdigit() and x != '.', value), ''))
        except Exception as e:
            pass # 데이터가 꼬여서 와도 무시하고 기본값 반환
            
        return parsed_data

    async def _notification_handler(self, sender, data):
        """데이터 수신 시 브레이크를 작동시켜도 통신이 끊기지 않도록 분리"""
        try:
            raw_text = data.decode('utf-8').strip()
            clean_data = self._parse_data(raw_text)
            
            if self.on_data_received:
                # [해결책 1] 메인 로직(브레이크 작동 등)을 별도의 쓰레드(Background)로 던짐!
                # 이렇게 하면 브레이크가 1초 동안 time.sleep()을 해도 블루투스는 계속 돌아갑니다.
                asyncio.to_thread(self.on_data_received, clean_data)
                
        except Exception as e:
            print(f"⚠️ [BLE] 데이터 처리 에러: {e}")

    async def start_listening(self):
        """무한 재연결을 보장하는 메인 루프"""
        print(f"🔍 블루투스 스캔 시작... (목표 기기: {self.device_name})")
        
        while True:
            try:
                self._disconnect_event.clear() # 이벤트 초기화
                
                # 1. 기기 찾기
                device = await BleakScanner.find_device_by_name(self.device_name, timeout=5.0)
                if device is None:
                    print(f"⏳ {self.device_name} 찾는 중...")
                    continue

                # 2. 기기 연결 시도 (끊김 감지 콜백 등록)
                print(f"🔗 {self.device_name} 발견! 연결 시도 중...")
                async with BleakClient(device, disconnected_callback=self._disconnect_callback) as client:
                    self.is_connected = True
                    print("✅ 헬멧과 연결 완료! 데이터 수신 중...")
                    
                    # 3. 데이터 수신 알림 켜기
                    await client.start_notify(self.char_uuid, self._notification_handler)
                    
                    # [해결책 2] 끊김 이벤트가 발생할 때까지 무한 대기 (CPU 점유율 최소화)
                    await self._disconnect_event.wait()
                    
            except Exception as e:
                print(f"⚠️ [BLE] 스캔/연결 중 에러 발생: {e}")
                await asyncio.sleep(2) # 에러 시 2초 쉬고 다시 시도