import serial
import time

GPS_PORT = "/dev/serial0"
BAUDRATE = 9600

def test_gps():
    print("🛰️ GPS 모듈 테스트를 시작합니다. (Ctrl+C로 종료)")
    print("주의: 실내에서는 위성을 잡을 수 없어 데이터가 비어있을 수 있습니다.")
    
    try:
        # 타임아웃을 1초로 설정하여 멈춤 방지
        gps = serial.Serial(GPS_PORT, BAUDRATE, timeout=1)
        gps.reset_input_buffer()
        
        while True:
            if gps.in_waiting > 0:
                # 라인 단위로 읽어오기
                line = gps.readline().decode('utf-8', errors='ignore').strip()
                
                # 모든 NMEA 데이터를 보고 싶다면 아래 주석을 해제하세요
                # print(f"[RAW] {line}")
                
                # 자전거 시스템의 핵심인 위치/속도 데이터(GPRMC)만 필터링
                if line.startswith('$GPRMC'):
                    parts = line.split(',')
                    if len(parts) >= 10:
                        status = parts[2] # 'A'=Active(수신성공), 'V'=Void(수신실패/위성못잡음)
                        
                        if status == 'A':
                            raw_lat = float(parts[3])
                            lat = int(raw_lat / 100) + ((raw_lat % 100) / 60.0)
                            
                            raw_lon = float(parts[5])
                            lon = int(raw_lon / 100) + ((raw_lon % 100) / 60.0)
                            
                            speed_knots = float(parts[7])
                            speed_kmh = speed_knots * 1.852
                            
                            print(f"✅ [수신 성공] 위도: {lat:.5f}, 경도: {lon:.5f}, 속도: {speed_kmh:.1f} km/h")
                        else:
                            print("⏳ [수신 대기] 위성을 찾고 있습니다... (야외로 이동해주세요)")
            time.sleep(0.1)

    except Exception as e:
        print(f"⚠️ GPS 포트 열기 실패: {e}")
        print("힌트: sudo raspi-config 에서 Serial Port 하드웨어가 활성화되어 있는지 확인하세요.")

if __name__ == "__main__":
    try:
        test_gps()
    except KeyboardInterrupt:
        print("\n🛑 테스트 종료")