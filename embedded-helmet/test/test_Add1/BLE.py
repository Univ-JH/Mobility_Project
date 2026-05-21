import asyncio
import struct
from bleak import BleakClient, BleakScanner

# 아두이노에 설정된 UUID 및 기기 이름 고정
HELMET_NAME = "SmartHelmet_Alpha"
STATUS_CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
EVENT_CHAR_UUID = "19B10002-E8F2-537E-4F6C-D104768A1214"

# [수정 완료] 아두이노 구조체 규격과 100% 일치하도록 포맷 변경
# schemaVersion(B, 1) + seq(I, 4) + timestamp(I, 4) + rideId(I, 4) + eventLabel(B, 1) = 총 14바이트
EVENT_STRUCT_FORMAT = "<BIIIB"

def decode_event_label(label):
    mapping = {
        1: "EMERGENCY: 전도 (Fall)",
        2: "EMERGENCY: 충돌 (Crash)",
        3: "EMERGENCY: 급가속",
        4: "EMERGENCY: 급정거",
        5: "ALERT: 충돌 후 이탈 의심 (Crash to Idle)"
    }
    return mapping.get(label, f"알 수 없는 이벤트 ({label})")

# 1. 헬멧 착용 상태 알림 콜백
def status_notification_handler(sender, data):
    status = data[0]
    status_text = "착용됨 (WORN)" if status == 1 else "벗음 (IDLE)"
    print(f"\n[STATUS CHANGE] 헬멧 상태: {status_text}")

# 2. 사고 감지 이벤트 알림 콜백
def event_notification_handler(sender, data):
    # 통신 유실 등으로 데이터가 14바이트보다 부족하거나 넘칠 경우 보정
    if len(data) < 14:
        padded_data = data + b'\x00' * (14 - len(data))
    else:
        padded_data = data[:14]

    try:
        # 정확히 14바이트 포맷(<BIIIB)으로 언팩 진행
        schema_ver, seq, timestamp, ride_id, event_label = struct.unpack(EVENT_STRUCT_FORMAT, padded_data)
        event_name = decode_event_label(event_label)
        
        print("-" * 50)
        print(f"[EVENT RECEIVED] {event_name}")
        print(f"  - 스키마 버전 : {schema_ver}")
        print(f"  - 이벤트 번호 : #{seq}")
        print(f"  - 구동 시간   : {timestamp / 1000.0:.2f} 초")
        print(f"  - 라이딩 ID   : {ride_id}")
        print("-" * 50)
    except Exception as e:
        print(f"[ERROR] 데이터 파싱 중 오류 발생: {e}")

async def main():
    print(f"'{HELMET_NAME}' 기기를 검색 중입니다...")
    
    # 헬멧 장치 스캔 (타이밍 아웃 10초)
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and HELMET_NAME in d.name, timeout=10.0
    )
    
    if not device:
        print(f"오류: '{HELMET_NAME}' 기기를 찾을 수 없습니다. 아두이노 전원을 확인하세요.")
        return

    print(f"기기 발견! 연결을 시도합니다. [주소: {device.address}]")

    # BLE 연결 및 알림 구독
    async with BleakClient(device) as client:
        if client.is_connected:
            print(f"성공: {HELMET_NAME}에 연결되었습니다.")
            
            # 각 Characteristic 알림(Notify) 구독 시작
            await client.start_notify(STATUS_CHAR_UUID, status_notification_handler)
            await client.start_notify(EVENT_CHAR_UUID, event_notification_handler)
            
            print("데이터 수신 대기 중... (종료하려면 Ctrl+C)")
            
            # 대기 루프 주기를 0.1초로 설정하여 반응성 유지
            while True:
                await asyncio.sleep(0.1)
        else:
            print("오류: 기기 연결에 실패했습니다.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n라즈베리파이 수신 프로그램을 종료합니다.")