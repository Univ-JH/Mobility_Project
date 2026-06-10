import serial
import time

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 시리얼(UART) 데이터 수신 최종 테스트")
    print("=" * 60)
    print("⚠️ 주의: 센서 뒷면의 DIP 스위치가 반드시 'UART'로 되어 있어야 합니다!\n")
    
    try:
        # GPS가 쓰던 포트를 빌려 9600 속도로 연결 (센서 기본 속도)
        ser = serial.Serial('/dev/serial0', 9600, timeout=1)
        ser.reset_input_buffer()
        print("✅ 포트 접속 성공! 센서 데이터를 기다립니다...")
    except Exception as e:
        print(f"❌ 포트 열기 실패: {e}")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                raw_data = ser.read(ser.in_waiting)
                
                # 1. 헥사(HEX) 코드 형태로 출력 (데이터 프레임 확인용)
                hex_data = ' '.join([f"{b:02X}" for b in raw_data])
                
                # 2. 텍스트 형태로 출력 (ASCII 문자가 섞여 있을 경우)
                text_data = "".join([chr(b) if 32 <= b <= 126 else "." for b in raw_data])
                
                print(f"📦 [HEX 데이터]: {hex_data}")
                print(f"📩 [TXT 데이터]: {text_data}\n")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 테스트 종료")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()