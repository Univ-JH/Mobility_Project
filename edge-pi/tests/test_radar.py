import serial
import time

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 통신속도 자동 탐색 & 수신 테스트")
    print("=" * 60)
    
    # mmWave 센서들이 주로 사용하는 속도들을 모두 찔러봅니다.
    baud_rates = [115200, 256000, 9600, 57600, 19200, 38400]
    working_ser = None

    for baud in baud_rates:
        print(f"🔍 [테스트] 통신 속도 {baud} bps 시도 중...")
        try:
            ser = serial.Serial('/dev/serial0', baud, timeout=1)
            ser.reset_input_buffer()
            
            # 3초간 귀를 기울여봅니다.
            end_time = time.time() + 3
            while time.time() < end_time:
                if ser.in_waiting > 0:
                    raw = ser.read(ser.in_waiting)
                    print(f"\n✅ 빙고! {baud} bps에서 센서 데이터를 찾았습니다!")
                    working_ser = ser
                    break
                time.sleep(0.1)
            
            if working_ser:
                break  # 찾았으면 다음 속도 테스트 중지
            else:
                ser.close() # 못 찾았으면 포트 닫고 다음 속도로
                
        except Exception as e:
            print(f"❌ 포트 에러 ({baud}): {e}")

    # 모든 속도에서 응답이 없을 경우의 해결책 안내
    if not working_ser:
        print("\n❌ 모든 통신 속도에서 센서의 응답이 없습니다.")
        print("💡 [즉각 해결책]: 지금 라즈베리파이에 꽂혀있는 물리 8번, 10번 핀의 선을 서로 '맞바꿔서' 꽂아주세요!")
        print("   (c/r을 10번에, d/t를 8번에 꽂고 코드를 다시 실행하시면 무조건 잡힙니다)")
        return

    # 통신 성공 시 실시간 데이터 출력 시작
    print("\n🚀 실시간 데이터 수신을 시작합니다 (종료: Ctrl+C)\n")
    try:
        while True:
            if working_ser.in_waiting > 0:
                raw_data = working_ser.read(working_ser.in_waiting)
                
                # 데이터 덩어리 확인
                hex_data = ' '.join([f"{b:02X}" for b in raw_data])
                text_data = "".join([chr(b) if 32 <= b <= 126 else "." for b in raw_data])
                
                print(f"📦 [HEX]: {hex_data}")
                print(f"📩 [TXT]: {text_data}\n")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 테스트 종료")
    finally:
        working_ser.close()

if __name__ == "__main__":
    main()