import time
import smbus2

I2C_BUS = 1
TARGET_ADDR = 0x2A  # 아까 스캔에서 나왔던 센서 주소 (만약 0x2B였다면 수정해주세요)

def raw_data_scanner():
    print("📡 [단독 실행] mmWave Raw Data 다이렉트 스캐너 시작")
    print("센서가 보내는 데이터 보따리를 통째로 해독합니다...")
    print("-" * 50)
    
    try:
        bus = smbus2.SMBus(I2C_BUS)
    except Exception as e:
        print(f"⚠️ I2C 버스를 열 수 없습니다: {e}")
        return

    try:
        while True:
            try:
                # 센서의 0번 방부터 16바이트의 데이터를 한 번에 긁어옵니다.
                data_block = bus.read_i2c_block_data(TARGET_ADDR, 0x00, 16)
                
                # 배열 형태로 보기 좋게 출력 (예: [85, 170, 1, 0, 15, ...])
                print(f"📦 실시간 데이터: {data_block}")
                
            except OSError:
                print("⚠️ 통신 딜레이 (센서가 데이터를 준비 중입니다)")
                
            # 눈으로 숫자가 바뀌는 걸 확인하기 위해 0.5초 대기
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n🛑 테스트가 사용자에 의해 종료되었습니다.")
    finally:
        bus.close()
        print("🧹 통신 포트 닫힘")

if __name__ == "__main__":
    raw_data_scanner()