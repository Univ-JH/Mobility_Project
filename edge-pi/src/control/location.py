# pip install pyserial smbus2
import serial
import smbus2
import threading
import time
import math

from src.communication.comm_config import (
    GPS_SERIAL_PORT, GPS_BAUDRATE, 
    IMU_I2C_ADDRESS, IMU_SHOCK_THRESHOLD
)

class LocationMotionSensor:
    def __init__(self):
        self.data_lock = threading.Lock()
        
        self.current_data = {
            "lat": 0.0,             
            "lon": 0.0,             
            "speed": 0.0,           
            "bike_shock": False     
        }
        self.is_running = False
        
        # [수정 1] 충격 감지 유지 타이머 변수
        self.shock_until = 0.0 
        
        # --- GPS (SZH-NEO02) 초기화 ---
        try:
            self.gps = serial.Serial(GPS_SERIAL_PORT, GPS_BAUDRATE, timeout=1)
            self.gps.reset_input_buffer() # [수정 3] 연결 전 쌓인 쓰레기 데이터 비우기
            print(f"🛰️ [센서] GPS 포트 열림: {GPS_SERIAL_PORT}")
        except Exception as e:
            self.gps = None
            print(f"⚠️ [센서] GPS 연결 실패: {e}")

        # --- IMU (ATN-G04) 초기화 ---
        try:
            self.bus = smbus2.SMBus(1)
            self.bus.write_byte_data(IMU_I2C_ADDRESS, 0x6B, 0)
            print(f"🧭 [센서] IMU 연결 성공: 0x{IMU_I2C_ADDRESS:02X}")
        except Exception as e:
            self.bus = None
            print(f"⚠️ [센서] IMU 연결 실패: {e}")

    def _read_imu_word(self, reg):
        if not self.bus: return 0
        try:
            h = self.bus.read_byte_data(IMU_I2C_ADDRESS, reg)
            l = self.bus.read_byte_data(IMU_I2C_ADDRESS, reg+1)
            value = (h << 8) + l
            return -((65535 - value) + 1) if value >= 0x8000 else value
        except Exception:
            return 0

    # ========================================================
    # [스레드 1] IMU 고속 처리 스레드 (50Hz)
    # ========================================================
    def _imu_loop(self):
        print("⚡ [센서] IMU 충격 감지 고속 스레드 가동")
        while self.is_running:
            if self.bus:
                try:
                    acc_x = self._read_imu_word(0x3B) / 16384.0
                    acc_y = self._read_imu_word(0x3D) / 16384.0
                    acc_z = self._read_imu_word(0x3F) / 16384.0
                    
                    total_g = math.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
                    
                    # 순간 충격이 임계치를 넘으면, 현재 시간 + 2초 동안 상태 유지
                    if total_g > IMU_SHOCK_THRESHOLD:
                        self.shock_until = time.time() + 2.0
                        
                except Exception:
                    pass # I2C 튀는 현상 무시
                
                with self.data_lock:
                    # 현재 시간이 유지 시간(shock_until)을 넘지 않았다면 계속 True 유지
                    self.current_data["bike_shock"] = time.time() < self.shock_until
            
            time.sleep(0.02) 

    # ========================================================
    # [스레드 2] GPS 저속 처리 스레드 (5Hz)
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
        self.imu_thread = threading.Thread(target=self._imu_loop, daemon=True)
        self.gps_thread = threading.Thread(target=self._gps_loop, daemon=True)
        self.imu_thread.start()
        self.gps_thread.start()

    def get_sensor_data(self):
        with self.data_lock:
            return self.current_data.copy()

    def stop(self):
        self.is_running = False
        if hasattr(self, 'imu_thread'): self.imu_thread.join()
        if hasattr(self, 'gps_thread'): self.gps_thread.join()
        
        if self.gps: 
            self.gps.close()
        # I2C 통신 버스 자원 안전 반환
        if self.bus: 
            self.bus.close()
            
        print("🧹 [센서] 위치 및 모션 모듈 안전 종료")