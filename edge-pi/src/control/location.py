# pip install pyserial
import serial
import threading
import time

# 사용자님의 기존 comm_config 경로에서 GPS 설정만 가져옵니다.
from src.communication.comm_config import (
    GPS_SERIAL_PORT, GPS_BAUDRATE
)

class LocationMotionSensor:
    def __init__(self):
        self.data_lock = threading.Lock()
        
        # [변수명 유지] 다른 코드들과 완벽하게 연동되도록 기존 딕셔너리 키를 그대로 유지합니다.
        self.current_data = {
            "lat": 0.0,             
            "lon": 0.0,             
            "speed": 0.0,           
            "bike_shock": False     # IMU 센서가 제거되었으므로 항상 False 안전 패딩 처리
        }
        self.is_running = False
        
        # --- GPS (SZH-NEO02) 초기화 ---
        try:
            self.gps = serial.Serial(GPS_SERIAL_PORT, GPS_BAUDRATE, timeout=1)
            self.gps.reset_input_buffer() # 연결 전 버퍼에 쌓인 쓰레기 데이터 비우기
            print(f"🛰️ [센서] GPS 포트 열림 성공: {GPS_SERIAL_PORT}")
        except Exception as e:
            self.gps = None
            print(f"⚠️ [센서] GPS 연결 실패: {e}")

    # ========================================================
    # [스레드] GPS 데이터 처리 스레드 (5Hz)
    # ========================================================
    def _gps_loop(self):
        print("🛰️ [센서] GPS 위치 데이터 수집 스레드 가동")
        while self.is_running:
            if self.gps and self.gps.in_waiting > 0:
                try:
                    line = self.gps.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('$GPRMC'):
                        parts = line.split(',')
                        
                        # 유효한 GPS 데이터 상태('A') 일 때만 파싱 수행
                        if len(parts) >= 10 and parts[2] == 'A': 
                            raw_lat = float(parts[3])
                            parsed_lat = int(raw_lat / 100) + ((raw_lat % 100) / 60.0)
                            if parts[4] == 'S': parsed_lat = -parsed_lat
                            
                            raw_lon = float(parts[5])
                            parsed_lon = int(raw_lon / 100) + ((raw_lon % 100) / 60.0)
                            if parts[6] == 'W': parsed_lon = -parsed_lon
                            
                            parsed_speed = float(parts[7]) * 1.852 
                            
                            with self.data_lock:
                                self.current_data["lat"] = parsed_lat
                                self.current_data["lon"] = parsed_lon
                                self.current_data["speed"] = parsed_speed
                except Exception:
                    pass # 순간적인 시리얼 통신 노이즈는 안전하게 무시합니다.
            
            time.sleep(0.2) 

    def start(self):
        self.is_running = True
        # IMU 스레드는 제외하고, 오직 GPS 스레드만 안전하게 생성하여 가동합니다.
        self.gps_thread = threading.Thread(target=self._gps_loop, daemon=True)
        self.gps_thread.start()

    def get_sensor_data(self):
        """main.py 메인 루프에서 센서 스냅샷을 찍을 때 호출하는 함수"""
        with self.data_lock:
            return self.current_data.copy()

    def stop(self):
        """시스템 안전 종료 시 자원 해제"""
        self.is_running = False
        if hasattr(self, 'gps_thread'): 
            self.gps_thread.join(timeout=1.0)
        
        if self.gps: 
            self.gps.close()
            
        print("Cleaned up Location resource.")