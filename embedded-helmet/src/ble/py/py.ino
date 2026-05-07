import asyncio
from bleak import BleakClient

# 1단계에서 확인한 아두이노의 맥 주소를 여기에 넣으세요!
DEVICE_ADDRESS = "06:a1:eb:77:98:58" 
# 아두이노 코드와 반드시 일치해야 함
CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

async def main():
    print(f"{DEVICE_ADDRESS}에 연결 시도 중...")
    
    try:
        # 연결 시도 (타임아웃 10초)
        async with BleakClient(DEVICE_ADDRESS, timeout=10.0) as client:
            if client.is_connected:
                print("✅ 연결 성공!")
                
                # 5번 정도 데이터를 읽어봅시다
                for i in range(5):
                    raw_data = await client.read_gatt_char(CHARACTERISTIC_UUID)
                    # 바이트를 정수로 변환
                    value = int.from_bytes(raw_data, byteorder='little')
                    print(f"[{i+1}] 아두이노 데이터: {value}")
                    await asyncio.sleep(1)
                    
                print("연결을 종료합니다.")
            else:
                print("연결 실패")
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())