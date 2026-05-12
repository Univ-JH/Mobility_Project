import asyncio
from bleak import BleakScanner, BleakClient

from src.communication.comm_config import BLE_DEVICE_NAME, BLE_CHAR_UUID

class HelmetBLEManager:
    def __init__(self):
        self.device_name = BLE_DEVICE_NAME
        self.char_uuid = BLE_CHAR_UUID
        self.is_connected = False
        self.on_data_received = None 
        
        self.last_sequence = -1
        self._disconnect_event = asyncio.Event() 

    def _disconnect_callback(self, client):
        print("\n [BLE] 헬멧 연결 끊김 감지 (수동 주행 허용 대기)")
        self.is_connected = False
        self._disconnect_event.set()

    def _parse_data(self, raw_data):
        """안전한 패킷 파싱"""
        result = {"seq": -1, "is_worn": True, "is_accident": False, "speed": 0.0}
        try:
            decoded = raw_data.decode('utf-8', errors='ignore').replace('\x00', '').strip()
            parts = decoded.split(',')
            for part in parts:
                if ':' not in part: continue
                key, val = part.split(':', 1)
                val = val.strip()
                if not val: continue 
                
                if key == 'Q': result['seq'] = int(val)
                elif key == 'W': result['is_worn'] = (val == '1')
                elif key == 'A': result['is_accident'] = (val == '1')
                elif key == 'S': result['speed'] = float(val)
        except Exception:
            pass 
        return result

    async def _notification_handler(self, sender, data):
        """데이터 수신 및 시퀀스 필터링"""
        parsed_data = self._parse_data(data)
        new_seq = parsed_data["seq"]

        if new_seq > self.last_sequence or (new_seq == 0 and self.last_sequence > 100):
            self.last_sequence = new_seq
            if self.on_data_received:
                asyncio.to_thread(self.on_data_received, parsed_data)

    async def start_listening(self):
        """BLE 스캔 및 무한 재연결 루프"""
        print(f"🔍 [BLE] {self.device_name} 탐색 중...")
        while True:
            try:
                self._disconnect_event.clear()
                device = await BleakScanner.find_device_by_name(self.device_name, timeout=5.0)
                
                if device is None:
                    continue

                async with BleakClient(device, disconnected_callback=self._disconnect_callback) as client:
                    self.is_connected = True
                    print(f"✅ [BLE] {self.device_name} 연결 성공!")
                    await client.start_notify(self.char_uuid, self._notification_handler)
                    await self._disconnect_event.wait()
                    
            except Exception as e:
                await asyncio.sleep(2)