import smbus2
import time

RADAR_I2C_ADDR = 0x2A

def main():
    print("=" * 70)
    print("📡 mmWave 레이더 I2C 내부 레지스터(방 번호) 정밀 탐색기")
    print("=" * 70)
    
    try:
        bus = smbus2.SMBus(1)
    except Exception as e:
        print(f"❌ I2C 버스 에러: {e}")
        return

    print("💡 [테스트 방법] 센서 앞에서 손을 흔들며 아래 숫자들을 매의 눈으로 지켜보세요!")
    print("💡 129처럼 가만히 있는 숫자 말고, 움직일 때마다 '0에서 1' 또는 '다른 숫자'로 확확 바뀌는 방(R)을 찾으시면 됩니다.\n")
    time.sleep(2)
    
    try:
        while True:
            regs = []
            # 0번 방(0x00)부터 15번 방(0x0F)까지 데이터 싹 다 읽어오기
            for reg in range(0x00, 0x10):
                try:
                    val = bus.read_byte_data(RADAR_I2C_ADDR, reg)
                    # 보기 편하게 R00: 값 형태로 저장
                    regs.append(f"R{reg:02X}:{val:3d}")
                except Exception:
                    regs.append(f"R{reg:02X}:ERR")
            
            # 터미널 한 줄에 모든 방의 데이터를 실시간으로 출력
            print("\r" + " | ".join(regs), end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 탐색 종료")
    finally:
        bus.close()

if __name__ == "__main__":
    main()