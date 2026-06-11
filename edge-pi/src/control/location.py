# pip install pyserial
import serial
import threading
import time

from src.communication.comm_config import (
    GPS_SERIAL_PORT, GPS_BAUDRATE
)

class LocationMotionSensor:
    def __init__(self):
        self.data_lock = threading.Lock()
        
        # main.py 와의 완벽한 호환성을 위해 딕셔너리 구조 그대로 유지
        self.current_data = {
            "lat": 0.0,             
            "lon": 0.0,             
            "speed": 0.0,           
            "bike_shock": False     # IMU가 없으므로 항상 False로 안전 유지
        }
        self.is_running = False
        
        # --- GPS (SZH-NEO02) 초기화 ---
        try:
            self.gps = serial.Serial(GPS_SERIAL_PORT, GPS_BAUDRATE, timeout=1)
            self.gps.reset_input_buffer()
            print(f"🛰️ [센서] GPS 포트 열림: {GPS_SERIAL_PORT}")
        except Exception as e:
            self.gps = None
            print(f"⚠️ [센서] GPS 연결 실패: {e}")

    # ========================================================
    # [스레드] GPS 저속 처리 스레드 (5Hz)
    # ========================================================
    def _gps_loop(self):
        print("🛰️ [센서] GPS 위치 데이터 수집 스레드 가동")
        while self.is_running:
            if self.gps and self.gps.in_waiting > 0:
                try:
                    line = self.gps.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('$GPRMC'):
                        parts = line.split(',')
                        
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
                    pass 
            
            time.sleep(0.2) 

    def start(self):
        self.is_running = True
        # IMU 스레드를 지우고 GPS 스레드만 단독 실행
        self.gps_thread = threading.Thread(target=self._gps_loop, daemon=True)
        self.gps_thread.start()

    def get_sensor_data(self):
        with self.data_lock:
            return self.current_data.copy()

    def stop(self):
        self.is_running = False
        if hasattr(self, 'gps_thread'):
            self.gps_thread.join(timeout=2.0)
        
        if self.gps: 
            self.gps.close()
            
        print("🧹 [센서] 위치 모듈 안전 종료")