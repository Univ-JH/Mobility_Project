import asyncio
from bleak import BleakClient, BleakScanner

# 아두이노 코드에 적힌 것과 똑같아야함
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# 아두이노의 MAC 주소를 입력하세요 (모르면 빈칸)
HELMET_MAC_ADDRESS = "" # 예: "A0:B1:C2:D3:E4:F5"
HELMET_NAME = "SmartHelmet_01"

async def notification_handler(sender: int, data: bytearray):
    """헬멧에서 데이터(Notify)가 날아올 때마다 자동 실행되는 함수"""
    try:
        # 1. Byte 배열을 읽을 수 있는 문자열로 변환 (엔디언 문제 해결)
        raw_text = data.decode('utf-8')

        # 2. 콘솔에 예쁘게 출력
        print(f"[{sender}] 수신 데이터: {raw_text}")

    except Exception as e:
        print(f"데이터 파싱 에러: {e}")

async def run():
    print(f"🔍 헬멧({HELMET_NAME})을 스캔하는 중...")

    # MAC 주소를 모를 경우 이름으로 스캔하여 찾기
    device = None
    if HELMET_MAC_ADDRESS:
        device = await BleakScanner.find_device_by_address(HELMET_MAC_ADDRESS, timeout=10.0)
    else:
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name == HELMET_NAME:
                device = d
                print(f"🎉 헬멧 발견! MAC 주소: {device.address}")
                break

    if not device:
        print("❌ 헬멧을 찾을 수 없습니다. 전원이 켜져 있는지 확인하세요.")
        return

    # 헬멧 연결 시작
    print(f"🔄 {device.address} 에 연결 시도 중...")
    async with BleakClient(device.address) as client:
        print(f"✅ 연결 성공! (연결 상태: {client.is_connected})")

        # Characteristic 구독 (Notify) 시작 -> 날아오는 데이터를 notification_handler로 보냄
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        print("📥 데이터 수신 대기 중... (종료하려면 Ctrl+C)")

        # 무한 대기 (이 루프가 살아있어야 계속 데이터를 받음)
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[종료] 사용자가 프로그램을 중지했습니다.")