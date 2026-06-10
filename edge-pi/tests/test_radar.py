import smbus2
import time

def scan_i2c():
    print("=" * 60)
    print("📡 mmWave 레이더 I2C 모드 스캔 테스트")
    print("=" * 60)
    
    try:
        bus = smbus2.SMBus(1)
        print("✅ I2C 버스 오픈 성공! 센서 주소를 탐색합니다...\n")
    except Exception as e:
        print(f"❌ I2C 버스 열기 실패: {e}")
        print("💡 터미널에 'sudo raspi-config'를 입력하고 [Interfacing Options] -> [I2C]를 Enabled로 켜주세요.")
        return

    found = []
    for addr in range(0x03, 0x78):
        try:
            # 해당 주소에 말을 걸어보고 응답이 오면 리스트에 추가
            bus.read_byte(addr)
            found.append(addr)
            print(f"🎉 빙고! I2C 주소 [ 0x{addr:02X} ] 에서 레이더 센서를 발견했습니다!")
        except Exception:
            pass

    if not found:
        print("❌ 아무 장치도 찾지 못했습니다.")
        print("💡 [확인사항] d/t 선이 물리 3번에, c/r 선이 물리 5번에 정확히 꽂혀있는지 핀 위치를 다시 확인해주세요.")
    else:
        print("\n🚀 [대성공] 레이더가 I2C 모드로 완벽하게 살아있습니다!")
        print("위에서 발견된 '0xOO' 주소를 알려주시면, 그 주소에 맞춰 레이더 감지 코드를 바로 완성해 드립니다.")

if __name__ == "__main__":
    scan_i2c()