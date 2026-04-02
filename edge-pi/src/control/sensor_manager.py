# 도구 불러오기
import serial  # 시리얼 통신 도구
from gpiozero import DistanceSensor  # 거리 측정 도구

# 센서 관리 설계도
class SensorManager:
    
    # 초기 설정
    def __init__(self, config):
        # 초음파 센서 핀 연결
        self.dist_sensor = DistanceSensor(
            echo=config['HW_PINS']['ECHO'],  # 받는 핀
            trigger=config['HW_PINS']['TRIG']  # 보내는 핀
        )
        
        # 블루투스 통신 연결
        try:
            # 설정값에 맞춰 통로 열기
            self.bt_serial = serial.Serial(config['HW_PINS']['BT_PORT'], 9600, timeout=1)
            print("[센서] 연결 성공")
        except:
            # 연결 안 될 경우 처리
            print("[센서] 연결 실패")
            self.bt_serial = None

    # 거리 측정 동작
    def get_distance(self):
        # 미터 단위로 거리 정보 전달
        return self.dist_sensor.distance

    # 헬멧 정보 읽기 동작
    def get_helmet_data(self):
        # 신호가 들어왔을 때만 실행
        if self.bt_serial and self.bt_serial.in_waiting > 0:
            # 한 줄 읽어오기
            line = self.bt_serial.readline().decode('utf-8').strip()
            
            # 쉼표 기준으로 나누기
            data_parts = line.split(',')
            
            # 정보 정리함
            result = {}
            for part in data_parts:
                if ':' in part:
                    key, value = part.split(':')
                    # 숫자 데이터를 참/거짓으로 변경
                    result[key] = True if value == '1' else False
            
            return result
        
        # 데이터 없을 때 기본값 전달
        return {"WORN": True, "FALL": False}