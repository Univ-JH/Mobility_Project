# 도구 가져오기
import json  # 설정 파일 읽기 도구
import time  # 시간 계산 도구
import cv2   # 카메라 영상 도구
from brake_system import BrakeSystem    # 2번 근육 모듈 연결
from sensor_manager import SensorManager  # 3번 감각 모듈 연결
from vision_ai import VisionAI          # 4번 시각 모듈 연결

# 전체 관리 설계도
class SafetySystemApp:
    
    # 초기 설정
    def __init__(self):
        # 설정 파일 열어서 수치들 가져오기
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        
        # 각 부품들 실제로 조립하기
        self.brake = BrakeSystem(self.config)    # 브레이크 연결
        self.sensors = SensorManager(self.config) # 센서들 연결
        self.vision = VisionAI()                # 인공지능 연결
        
        # 카메라 켜기
        self.cap = cv2.VideoCapture(0)
        
        # 시스템 가동 알림
        print("[시스템] 준비 완료")

    # 반복 실행 동작
    def run_logic(self):
        print("[시스템] 감시 시작")
        
        try:
            # 무한 반복 시작
            while True:
                # 카메라 사진 한 장 찍기
                ret, frame = self.cap.read()
                
                # 인공지능에게 길 종류 물어보기
                road_type = self.vision.predict_road_type(frame) if ret else "ROAD"
                
                # 센서들에게 거리와 헬멧 정보 물어보기
                dist = self.sensors.get_distance()
                h_data = self.sensors.get_helmet_data()

                # 명령서 양식 만들기 (팀 가이드라인 준수)
                cmd = {
                    "commandId": f"CMD-{int(time.time()*1000)}", # 명령 번호
                    "severity": "LOW",      # 중요도
                    "reason": "NORMAL",      # 사유
                    "ttlMs": self.config['THRESHOLD']['CMD_TTL_MS'], # 유효 시간
                    "target": "RELEASE"      # 목표 동작
                }

                # [우선순위 판단] 위험한 순서대로 검사하기
                
                # 1순위: 헬멧을 안 썼을 때
                if h_data.get("WORN") == False:
                    cmd.update({"target": "EMERGENCY", "reason": "헬멧 미착용", "severity": "CRITICAL"})
                
                # 2순위: 자전거가 넘어졌을 때
                elif h_data.get("FALL") == True:
                    cmd.update({"target": "EMERGENCY", "reason": "사고 발생", "severity": "CRITICAL"})
                
                # 3순위: 앞에 장애물이 너무 가까울 때
                elif dist < self.config['THRESHOLD']['CRITICAL_DIST_M']:
                    cmd.update({"target": "BRAKE", "reason": "장애물 근접", "severity": "HIGH"})
                
                # 4순위: 인도 주행 중일 때
                elif road_type == "SIDEWALK":
                    cmd.update({"target": "LIMIT", "reason": "인도 주행", "severity": "MEDIUM"})

                # 결정된 명령을 브레이크에 전달해서 움직이기
                self.brake.update_brake(cmd['target'])
                
                # 현재 상태 화면에 출력
                print(f"[기록] {cmd['reason']} -> 제동: {cmd['target']}")
                
                # 시간 지연 기능 (과부하 방지)
                time.sleep(0.05)

        except KeyboardInterrupt:
            # 종료 시 브레이크 풀고 안전하게 끄기
            print("[시스템] 종료 중")
            self.brake.update_brake("RELEASE")
            self.cap.release()

# 실제 실행
if __name__ == "__main__":
    app = SafetySystemApp()
    app.run_logic()