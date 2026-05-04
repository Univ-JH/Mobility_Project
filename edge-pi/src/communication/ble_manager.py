# pip install bleak
import asyncio
import time
import json
from typing import Callable, Optional
from bleak import BleakClient, BleakScanner

from .comm_config import (
    HELMET_MAC_ADDR, BLE_CHAR_DATA_UUID, 
    BLE_RECONNECT_INTERVAL, BLE_SCAN_TIMEOUT
)

class HelmetBLEManager:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.mac_addr = HELMET_MAC_ADDR
        self.client: Optional[BleakClient] = None
        
        # [RULE: 멱등성] 순서 역전 및 중복 데이터 방지
        self.last_seq = -1 
        
        # 외부 콜백
        self.on_data_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None

    def set_callbacks(self, on_data: Callable, on_disconnect: Callable):
        self.on_data_callback = on_data
        self.on_disconnect_callback = on_disconnect

    def _disconnected_handler(self, client):
        """[RULE: Fail-Safe] 연결 끊김 시 보수적 상태 전이 알림"""
        print(f"[JSON_LOG] {{\"eventType\": \"BLE_DISCONNECTED\", \"rideId\": \"{self.ride_id}\", \"severity\": \"HIGH\", \"reason\": \"Helmet Disconnected\"}}")
        if self.on_disconnect_callback:
            self.on_disconnect_callback()

    async def _notification_handler(self, sender: int, data: bytearray):
        """아두이노의 문자열 데이터를 수신하고 해석 (기존 방식 최적화)"""
        try:
            # 1. Byte를 문자열로 디코딩 (예: "Q:145,T:1714,W:1,A:0,S:0")
            raw_line = data.decode('utf-8').strip()
            
            # 2. 딕셔너리로 분리 및 매핑
            parsed_data = dict(item.split(":") for item in raw_line.split(","))
            
            # 3. Seq 검증 (중복/과거 데이터 버리기)
            current_seq = int(parsed_data.get('Q', -1))
            if current_seq <= self.last_seq and current_seq != 0:
                return  # 무시
            self.last_seq = current_seq

            # 4. 상태값 정수 변환 및 직관적인 키로 래핑
            status = {
                "seq": current_seq,
                "timestamp": int(parsed_data.get('T', time.time())),
                "is_worn": parsed_data.get('W') == '1',      # 1: 착용, 0: 미착용
                "is_accident": parsed_data.get('A') == '1',  # 1: 사고/전도, 0: 정상
                "speed_state": int(parsed_data.get('S', 0))  # 0: 정상, 1: 급감속, 2: 급가속
            }

            # 5. [RULE: 응급/강제 규칙] 치명적 상태 감지 시 즉각 로깅
            if not status["is_worn"]:
                self._log_warning("HELMET_REMOVED", "Helmet not worn")
            if status["is_accident"]:
                self._log_warning("FALL_DETECTED", "Accident or fall detected")
            if status["speed_state"] in [1, 2]:
                self._log_warning("DANGEROUS_ACCEL", f"Speed state: {status['speed_state']}")

            # 6. 메인 로직(Policy Engine)으로 데이터 전달
            if self.on_data_callback:
                self.on_data_callback(status)

        except Exception as e:
            # 파싱 실패 시 로그만 남기고 시스템은 멈추지 않음
            self._log_warning("BLE_PARSE_ERROR", f"Raw: {raw_line}, Error: {str(e)}")

    def _log_warning(self, event_type: str, reason: str):
        """구조화 로그 전송 유틸리티"""
        log = {"eventType": event_type, "rideId": self.ride_id, "severity": "HIGH", "reason": reason}
        print(f"[JSON_LOG] {json.dumps(log)}")

    async def connect_and_listen(self):
        """연결 유지 및 재연결 루프"""
        while True:
            try:
                print(f"[BLE_INFO] {self.mac_addr} 스캔 중...")
                device = await BleakScanner.find_device_by_address(self.mac_addr, timeout=BLE_SCAN_TIMEOUT)

                if not device:
                    await asyncio.sleep(BLE_RECONNECT_INTERVAL)
                    continue

                self.client = BleakClient(device, disconnected_callback=self._disconnected_handler)
                await self.client.connect()
                
                if self.client.is_connected:
                    print("[BLE_INFO] 헬멧 연결 성공! 데이터 수신 시작.")
                    await self.client.start_notify(BLE_CHAR_DATA_UUID, self._notification_handler)

                    while self.client.is_connected:
                        await asyncio.sleep(1)

            except Exception as e:
                self._log_warning("BLE_ERROR", str(e))
            
            finally:
                if self.client and self.client.is_connected:
                    await self.client.stop_notify(BLE_CHAR_DATA_UUID)
                    await self.client.disconnect()
                await asyncio.sleep(BLE_RECONNECT_INTERVAL)