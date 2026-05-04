import asyncio
from bleak import BleakClient

# 아두이노 코드에서 설정한 UUID (반드시 일치해야 함)
CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
# 아두이노의 MAC 주소 (미리 확인하거나 스캔을 통해 알아내야 함)
DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX" 

async def main(address):
    print(f"{address}에 연결 시도 중...")
    try:
        async with BleakClient(address) as client:
            print(f"연결 성공: {client.is_connected}")
            
            while True:
                # 데이터 읽기
                value = await client.read_gatt_char(CHARACTERISTIC_UUID)
                # 바이트 데이터를 정수로 변환 (little endian)
                int_value = int.from_bytes(value, byteorder='little')
                print(f"수신 데이터: {int_value}")
                
                await asyncio.sleep(1)
    except Exception as e:
        print(f"오류 발생: {e}")

# 장치를 찾지 못한 경우를 위해 스캔 먼저 수행하는 것을 추천합니다.
if __name__ == "__main__":
    asyncio.run(main(DEVICE_ADDRESS))