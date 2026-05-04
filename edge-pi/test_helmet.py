import asyncio
import sys
import os

# src 폴더를 인식하기 위한 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.communication.ble_manager import HelmetBLEManager

# 1. 데이터가 들어왔을 때 실행될 콜백 함수
def handle_helmet_data(status):
    print("\n" + "="*40)
    print(f" [수신 데이터] 시퀀스: {status['seq']}")
    print(f" - 착용 상태: {'✅ 착용 중' if status['is_worn'] else '❌ 미착용'}")
    print(f" - 사고 여부: {'🚨 사고 발생!' if status['is_accident'] else '✅ 정상'}")
    print(f" - 주행 상태: {status['speed_state']} (0:정상, 1:급감속, 2:급가속)")
    print(f" - 타임스탬프: {status['timestamp']}")
    print("="*40)

# 2. 연결이 끊겼을 때 실행될 콜백 함수
def handle_helmet_disconnect():
    print("\n[⚠️ 경고] 헬멧과의 연결이 끊겼습니다! 재연결을 시도합니다...")

async def main():
    print("=== [STEP 1] 헬멧 매니저 초기화 ===")
    # 테스트용 주행 ID 설정
    manager = HelmetBLEManager(ride_id="TEST_DRIVE_001")
    
    # 콜백 등록
    manager.set_callbacks(
        on_data=handle_helmet_data, 
        on_disconnect=handle_helmet_disconnect
    )
    
    print("=== [STEP 2] 스캔 및 연결 시작 (종료: Ctrl+C) ===")
    try:
        # 무한 재연결 루프 실행
        await manager.connect_and_listen()
    except asyncio.CancelledError:
        print("\n[INFO] 테스트가 중단되었습니다.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass