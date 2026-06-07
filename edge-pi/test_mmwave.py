import time
import smbus2

# 라즈베리 파이 5의 기본 I2C 버스는 1번입니다.
I2C_BUS = 1 

def scan_i2c(bus):
    """연결된 I2C 기기의 주소를 자동으로 찾습니다."""
    print("🔍 I2C 버스 스캔을 시작합니다...")
    found_addresses = []
    for addr in range(0x03, 0x78):
        try:
            # 해당 주소로 아주 짧은 신호를 보내 응답을 확인합니다.
            bus.write_quick(addr)
            found_addresses.append(addr)
        except OSError:
            pass
    return found_addresses

def test_mmwave():
    print("📡 [SEN0610] mmWave 레이더 센서 테스트")
    
    try:
        bus = smbus2.SMBus(I2C_BUS)
    except Exception as e:
        print(f"⚠️ I2C 버스를 열 수 없습니다. 설정(raspi-config)에서 I2C가 켜져 있는지 확인하세요. 에러: {e}")
        return

    # 1. 센서 연결 상태 및 주소 확인
    addresses = scan_i2c(bus)
    
    if not addresses:
        print("❌ 센서를 찾을 수 없습니다! 선 연결(SDA, SCL, 5V, GND)을 다시 확인해 주세요.")
        return
        
    print(f"✅ 발견된 I2C 기기 주소: {[hex(a) for a in addresses]}")
    
    # SEN0610의 기본 I2C 주소는 보통 0x2A 또는 0x2B입니다.
    # 만약 여러 개가 뜬다면 첫 번째 주소를 타겟으로 잡습니다.
    target_addr = addresses[0]
    print(f"🎯 타겟 센서(주소: {hex(target_addr)})와 통신을 시작합니다...\n")
    time.sleep(1)

    # 2. 데이터 수신 테스트 루프
    print("🚶‍♂️ 센서 앞에서 움직여보세요! (종료하려면 Ctrl+C)")
    print("-" * 50)
    
    try:
        while True:
            try:
                # 센서에서 1바이트의 기본 데이터를 읽어옵니다.
                # (DFRobot 센서는 보통 감지 상태가 변할 때 데이터를 보냅니다)
                data = bus.read_byte(target_addr)
                
                # 데이터 값에 따른 상태 출력 (센서 내부 펌웨어 버전에 따라 값이 다를 수 있음)
                if data > 0:
                    print(f"🚨 [감지됨] 사람 또는 물체의 움직임 포착! (Raw Data: {data})")
                else:
                    print(f"🟢 [대기중] 아무도 없습니다. (Raw Data: {data})")
                    
            except OSError as e:
                print(f"⚠️ 통신 에러 발생 (선이 흔들렸을 수 있습니다): {e}")
            
            # 센서 과부하 방지를 위해 0.2초 대기
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n🛑 테스트가 사용자에 의해 강제 종료되었습니다.")
    finally:
        bus.close()
        print("🧹 I2C 통신 포트 안전하게 닫힘")

if __name__ == "__main__":
    test_mmwave()