import serial
import time

def main():
    print("=" * 60)
    print("📡 DFRobot mmWave 레이더 시리얼(UART) 데이터 수신 테스트")
    print("=" * 60)
    
    try:
        # GPS가 쓰던 포트(/dev/serial0)를 레이더가 임시로 사용합니다 (통신속도 9600)
        ser = serial.Serial('/dev/serial0', 9600, timeout=1)
        print("✅ 시리얼 포트 접속 성공! 센서 데이터를 기다립니다...\n")
    except Exception as e:
        print(f"❌ 포트 열기 실패: {e}")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                raw_data = ser.read(ser.in_waiting)
                
                # 센서가 보내는 데이터가 알 수 없는 헥사(HEX) 코드일 수 있으므로 변환
                hex_data = ' '.join([f"{b:02X}" for b in raw_data])
                
                # 사람이 읽을 수 있는 텍스트가 섞여 있다면 같이 출력
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