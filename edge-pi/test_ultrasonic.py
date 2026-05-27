import time
from gpiozero import OutputDevice, InputDevice

# 핀 번호 설정 (BCM 기준 번호)
TRIG_PIN = 23
ECHO_PIN = 24

# 핀 초기화
trig = OutputDevice(TRIG_PIN)
echo = InputDevice(ECHO_PIN)

def get_distance():
    # 1. 센서 초기화 (안정화 대기)
    trig.off()
    time.sleep(0.01)

    # 2. 초음파 발사 명령 (10마이크로초 동안 Trig 핀 High)
    trig.on()
    time.sleep(0.00001)
    trig.off()

    # 3. Echo 핀이 High로 변할 때까지 대기 (발사 시작 시간)
    pulse_start = time.time()
    timeout_start = time.time()
    while echo.is_active == False:
        pulse_start = time.time()
        if time.time() - timeout_start > 0.1: # 타임아웃(센서 무응답 방어)
            return -1

    # 4. Echo 핀이 Low로 변할 때까지 대기 (초음파 수신 시간)
    pulse_end = time.time()
    timeout_start = time.time()
    while echo.is_active == True:
        pulse_end = time.time()
        if time.time() - timeout_start > 0.1:
            return -1

    # 5. 초음파가 날아갔다 돌아온 총 왕복 시간 계산
    pulse_duration = pulse_end - pulse_start

    # 6. 거리 수학적 계산 (음속: 초당 340m = 34000cm)
    # 왕복 거리이므로 2로 나누어 줍니다.
    distance = (pulse_duration * 34300) / 2
    
    return round(distance, 2)

if __name__ == "__main__":
    print("🦇 초음파 센서 거리 측정 테스트를 시작합니다. (종료: Ctrl+C)")
    time.sleep(2) # 초기 구동 대기
    
    try:
        while True:
            dist = get_distance()
            
            if dist == -1:
                print("⚠️ [에러] 센서 무응답 (배선이나 타임아웃을 확인하세요)")
            elif dist > 400 or dist < 2:
                print("⚠️ [경고] 측정 범위 이탈 (2cm ~ 400cm)")
            else:
                print(f"📏 현재 장애물 거리: {dist} cm")
            
            time.sleep(0.5) # 0.5초마다 측정
            
    except KeyboardInterrupt:
        print("\n🛑 측정을 종료합니다.")