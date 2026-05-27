import time
from gpiozero import Buzzer

# BCM 핀 번호 설정
BUZZER_PIN = 27

# 부저 객체 생성
buzzer = Buzzer(BUZZER_PIN)

def beep_warning():
    """가벼운 경고음 (장애물/인도 진입 시): 천천히 삑- 삑-"""
    print("🟡 [경고음] 삑 - 삑 - 삑 -")
    for _ in range(3):
        buzzer.on()
        time.sleep(0.3)
        buzzer.off()
        time.sleep(0.3)

def beep_emergency():
    """긴급 알람음 (사고/충돌 시): 아주 빠르게 삐삐삐삐!"""
    print("🔴 [긴급음] 삐삐삐삐삐삐!")
    for _ in range(10):
        buzzer.on()
        time.sleep(0.05)
        buzzer.off()
        time.sleep(0.05)

if __name__ == "__main__":
    print("🔊 부저(Buzzer) 사운드 테스트를 시작합니다.")
    time.sleep(1)
    
    try:
        while True:
            # 1. 경고음 테스트
            beep_warning()
            time.sleep(1)
            
            # 2. 긴급 알람음 테스트
            beep_emergency()
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 테스트를 종료합니다.")
        buzzer.off() # 프로그램 종료 시 소리가 계속 나는 현상 방지