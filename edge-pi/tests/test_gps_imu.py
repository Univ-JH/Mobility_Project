"""
GPS / IMU 위치·모션 센서 모듈 테스트
- GPS: 시리얼 포트 열기 → GPRMC NMEA 파싱 → 위·경도 수신 (/dev/ttyAMA0)
- IMU: I2C 통신 → 가속도 3축 읽기 → G-force 계산
- 10초간 데이터 수집 후 결과 보고

실행: python -m tests.test_gps_imu  (edge-pi/ 루트에서, 라즈베리파이 필수)
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.communication.comm_config import GPS_SERIAL_PORT, GPS_BAUDRATE, IMU_I2C_ADDRESS, IMU_SHOCK_THRESHOLD

COLLECT_SEC = 10


def test_imu():
    print("\n[1] IMU (ATN-G04) I2C 통신 및 G-force 측정")
    try:
        import smbus2
        import math
    except ImportError:
        print("  [SKIP] smbus2 미설치 — pip install smbus2")
        return

    try:
        bus = smbus2.SMBus(1)
        bus.write_byte_data(IMU_I2C_ADDRESS, 0x6B, 0)
        print(f"  PASS — IMU I2C 연결: 0x{IMU_I2C_ADDRESS:02X}")
    except Exception as e:
        print(f"  FAIL — I2C 연결 실패: {e}")
        return

    def read_word(reg):
        try:
            h = bus.read_byte_data(IMU_I2C_ADDRESS, reg)
            l = bus.read_byte_data(IMU_I2C_ADDRESS, reg + 1)
            v = (h << 8) + l
            return -((65535 - v) + 1) if v >= 0x8000 else v
        except Exception:
            return 0

    print(f"  {COLLECT_SEC}초간 G-force 샘플링 (충격 임계값: {IMU_SHOCK_THRESHOLD}G)")
    max_g = 0.0
    shock_detected = False
    start = time.time()
    sample_count = 0

    while time.time() - start < COLLECT_SEC:
        ax = read_word(0x3B) / 16384.0
        ay = read_word(0x3D) / 16384.0
        az = read_word(0x3F) / 16384.0
        total_g = math.sqrt(ax**2 + ay**2 + az**2)

        if total_g > max_g:
            max_g = total_g
        if total_g > IMU_SHOCK_THRESHOLD:
            shock_detected = True
            print(f"\n  충격 감지! G={total_g:.2f}G")

        print(f"\r  ax={ax:.2f} ay={ay:.2f} az={az:.2f}  total={total_g:.2f}G  max={max_g:.2f}G", end="", flush=True)
        sample_count += 1
        time.sleep(0.02)

    print(f"\n  샘플 수: {sample_count}  최대 G: {max_g:.2f}G  충격 감지: {shock_detected}")
    print(f"  {'PASS — 충격 감지 정상 작동' if shock_detected else 'INFO — 충격 없음 (센서 흔들어 확인 가능)'}")
    bus.close()


def test_gps():
    print(f"\n[2] GPS (SZH-NEO02) 시리얼 수신: {GPS_SERIAL_PORT} @ {GPS_BAUDRATE}bps")
    try:
        import serial
    except ImportError:
        print("  [SKIP] pyserial 미설치 — pip install pyserial")
        return

    try:
        ser = serial.Serial(GPS_SERIAL_PORT, GPS_BAUDRATE, timeout=1)
        ser.reset_input_buffer()
        print("  PASS — 시리얼 포트 열림")
    except Exception as e:
        print(f"  FAIL — 포트 열기 실패: {e}")
        return

    print(f"  {COLLECT_SEC}초간 NMEA 수신 대기 (위성 신호 필요)")
    fix_received = False
    start = time.time()

    while time.time() - start < COLLECT_SEC:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("$GPRMC"):
                    parts = line.split(",")
                    status = parts[2] if len(parts) > 2 else "?"
                    print(f"\r  GPRMC 수신: status={status}  raw={line[:40]}...", end="", flush=True)
                    if len(parts) >= 10 and status == "A":
                        raw_lat = float(parts[3])
                        lat = int(raw_lat / 100) + (raw_lat % 100) / 60.0
                        if parts[4] == "S":
                            lat = -lat
                        raw_lon = float(parts[5])
                        lon = int(raw_lon / 100) + (raw_lon % 100) / 60.0
                        if parts[6] == "W":
                            lon = -lon
                        spd = float(parts[7]) * 1.852
                        print(f"\n  위치 Fix: lat={lat:.6f} lon={lon:.6f} speed={spd:.1f}km/h")
                        fix_received = True
                        break
            except Exception:
                pass
        time.sleep(0.1)

    print(f"\n  {'PASS — GPS Fix 수신' if fix_received else 'FAIL — Fix 없음 (실외 환경 또는 위성 대기 필요)'}")
    ser.close()


def main():
    print("=" * 50)
    print("GPS / IMU 위치·모션 센서 모듈 테스트")
    print("=" * 50)
    test_imu()
    test_gps()


if __name__ == "__main__":
    main()
