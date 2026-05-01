import serial
import time

COMM_CONFIG = {
    "BT_PORT": "/dev/ttyS0",  # 라즈베리파이 5 블루투스 시리얼 포트 경로
    "BAUD_RATE": 9600,        # 통신 속도
    "TIMEOUT": 1,             # 수신 대기 시간 (초)
}

class ArduinoBLEComm:
    # 아두이노로부터 전처리된 센서 데이터를 수신하는 클래스
    def __init__(self):
        try:
            # 설정된 포트 정보를 바탕으로 시리얼 통신 시작
            self.ser = serial.Serial(
                port=COMM_CONFIG["BT_PORT"],
                baudrate=COMM_CONFIG["BAUD_RATE"],
                timeout=COMM_CONFIG["TIMEOUT"]
            )
            print(f"[통신] {COMM_CONFIG['BT_PORT']} 포트 연결 성공")
        except Exception as e:
            print(f"[오류] 아두이노 연결 실패: {e}")
            self.ser = None

    def receive_status(self):
        # 아두이노에서 보낸 전처리 데이터를 수신하고 해석
        # 수신 데이터 형식 예시: "W:1,A:0,S:0" 
        # (W:착용유무, A:사고유무, S:속도상태)
        if self.ser and self.ser.in_waiting > 0:
            try:
                # 1. 아두이노에서 보낸 문자열 읽기
                raw_line = self.ser.readline().decode('utf-8').strip()
                
                # 2. 문자열 분리 (쉼표와 콜론 기준)
                # 예: "W:1,A:0,S:0" -> {'W': '1', 'A': '0', 'S': '0'}
                data = dict(item.split(":") for item in raw_line.split(","))

                # 3. 아두이노에서 이미 연산된 값을 받아오므로, 정수 변환만 수행
                # W(Worn): 0(미착용), 1(착용)
                # A(Accident): 0(정상), 1(사고/전도)
                # S(Speed/Accel): 0(정상), 1(급감속), 2(급가속)
                status = {
                    "is_worn": data.get('W') == '1',
                    "is_accident": data.get('A') == '1',
                    "speed_state": int(data.get('S', 0)),
                    "timestamp": time.time() # 데이터 신선도 체크용
                }
                return status
                
            except Exception as e:
                print(f"[통신] 데이터 파싱 에러: {e}")
                return None
        return None

# 단독 테스트 코드 (통신 확인용)
if __name__ == "__main__":
    comm = ArduinoBLEComm()
    print("아두이노 데이터 수신 대기 중...")
    while True:
        current_status = comm.receive_status()
        if current_status:
            print(f"착용: {current_status['is_worn']} | "
                  f"사고: {current_status['is_accident']} | "
                  f"속도상태: {current_status['speed_state']}")
        time.sleep(0.1)