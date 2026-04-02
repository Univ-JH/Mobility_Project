# 도구 불러오기
import time  # 시간 기능
import threading  # 동시 작업 기능
from gpiozero import Servo  # 서보 모터 조절 도구
from gpiozero.pins.lgpio import LPiFactory  # 라즈베리파이 5 전용 설정 도구

# 브레이크 시스템 설계도
class BrakeSystem:
    
    # 초기 설정
    def __init__(self, config):
        # 라즈베리파이 5 전용 신호 공장 세팅
        factory = LPiFactory()
        
        # 실제 서보 모터 연결
        self.servo = Servo(
            config['HW_PINS']['SERVO'],  # 핀 번호 설정
            min_pulse_width=0.0005,      # 최소 신호 폭
            max_pulse_width=0.0025,      # 최대 신호 폭
            pin_factory=factory          # 전용 설정 연결
        )
        
        # 설정 파일에서 제동 단계표 가져오기
        self.levels = config['BRAKE_TABLE']
        
        # 현재 브레이크 위치 저장
        self.current_val = self.levels['RELEASE']
        
        # 처음에는 브레이크 해제 상태로 시작
        self.servo.value = self.current_val
        
        # 명령 꼬임 방지용 잠금 장치
        self._lock = threading.Lock()

    # 브레이크 강도 조절 동작
    def update_brake(self, target_name, step_delay=0.02):
        
        # 목표 단계의 숫자값 가져오기
        target_val = self.levels.get(target_name, 0.0)
        
        # 잠금 장치 가동
        with self._lock:
            # 부드러운 움직임을 위한 반복 계산
            while abs(self.current_val - target_val) > 0.05:
                
                # 목표치까지 조금씩 조이거나 풀기
                if self.current_val < target_val: 
                    self.current_val += 0.05
                else: 
                    self.current_val -= 0.05
                
                # 계산된 값을 모터에 전달
                self.servo.value = self.current_val
                
                # 시간 지연 기능
                time.sleep(step_delay)
            
            # 최종 목표치로 고정
            self.servo.value = target_val
            self.current_val = target_val
            
            # 상태 출력
            print(f"[제동] 단계 변경: {target_name}")