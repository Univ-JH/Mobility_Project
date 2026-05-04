import time
import traceback

# 초음파 센서 모듈 불러오기
from src.control.ultrasonic import UltrasonicSensor

def run_ultrasonic_test():
    print("=== [초음파 센서] 단독 정밀 측정 테스트 시작 ===")
    
    sensor = None
    try:
        # 1. 센서 객체 초기화
        # (클래스 내부에서 BCM 핀 설정 및 안정화 대기가 자동으로 진행됨)
        sensor = UltrasonicSensor()
        
        print("\n[READY] 센서 초기화 완료. 거리 측정을 시작합니다.")
        print("센서 앞에 손이나 물체를 대보고, 치워보세요. (종료: Ctrl+C)")
        print("-" * 50)
        time.sleep(1)

        # 2. 실시간 측정 루프
        while True:
            # (1) get_distance() 함수 호출
            distance = sensor.get_distance(ride_id="SENSOR_TEST_01")
            
            # (2) 결과 출력 포맷팅
            if distance == float('inf'):
                # 범위를 벗어나거나 에러(타임아웃 등)가 발생해 inf를 반환한 경우
                print("[측정 결과] ⚠️ 유효 범위를 벗어남 (또는 노이즈/타임아웃 방어 작동)")
            else:
                # 정상적으로 거리가 측정된 경우
                print(f"[측정 결과] 현재 전방 거리: {distance:.2f} cm")
            
            # 0.2초마다 측정 (1초에 5번)
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[사용자 중단] 테스트를 안전하게 종료합니다.")
    except Exception as e:
        print(f"\n[시스템 에러] {e}")
        traceback.print_exc()
    finally:
        # 3. 종료 시 GPIO 핀 안전하게 정리
        if sensor:
            sensor.cleanup()
        print("[CLEANUP] 프로그램이 종료되었습니다.")

if __name__ == "__main__":
    run_ultrasonic_test()