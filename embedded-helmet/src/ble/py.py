import asyncio
from bleak import BleakScanner, BleakClient

# 아두이노 코드와 동일한 UUID
CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

async def run():
    print("SmartHelmet_Test 장치를 찾는 중...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and "SmartHelmet_Test" in d.name
    )

    if not device:
        print("장치를 찾을 수 없습니다.")
        return

    print(f"연결 시도 중: {device.address}")
    async with BleakClient(device) as client:
        if client.is_connected:
            print("연결 성공!")
            
            # 데이터를 주기적으로 읽어옴
            for _ in range(10):
                value = await client.read_gatt_char(CHARACTERISTIC_UUID)
                # 바이트 데이터를 정수로 변환 (Little Endian)
                int_value = int.from_bytes(value, byteorder='little')
                print(f"아두이노에서 받은 값: {int_value}")
                await asyncio.sleep(1)
        else:
            print("연결 실패")

asyncio.run(run())