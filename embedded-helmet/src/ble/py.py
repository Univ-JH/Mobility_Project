import asyncio
from bleak import BleakScanner, BleakClient

# 아두이노에서 설정한 UUID와 동일해야 함
CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
DEVICE_NAME = "SmartHelmet_Alpha"

async def main():
    print("스마트 헬멧 탐색 중...")
    devices = await BleakScanner.discover()
    target_device = None
    
    for d in devices:
        if d.name == DEVICE_NAME:
            target_device = d
            break

    if not target_device:
        print("헬멧을 찾을 수 없습니다.")
        return

    async with BleakClient(target_device) as client:
        print(f"연결 성공: {target_device.address}")
        
        # 데이터 수신 시 콜백 함수
        def notification_handler(sender, data):
            status = int.from_bytes(data, byteorder='little')
            if status == 1:
                print("[상태] 헬멧 착용 확인 - 주행 가능(STANDBY)")
            elif status == 2:
                print("[위험] EMERGENCY 발생 - 긴급 제동 수행!")
            else:
                print("[상태] 미착용 - 구동 차단(LOCKED)")

        # 노티피케이션 시작 (실시간 수신)
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        
        while True:
            await asyncio.sleep(1) # 연결 유지

asyncio.run(main())