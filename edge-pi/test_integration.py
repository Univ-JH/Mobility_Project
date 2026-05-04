import time
import traceback

# 핵심 모듈 불러오기
from src.state.state_machine import SafetyStateMachine
from src.control.servo_control import BrakeController
from src.control.ultrasonic import UltrasonicSensor

def run_integration_test():
    print("=== [초음파 -> 상태기계 -> 서보 모터] 실물 통합 테스트 시작 ===")
    
    brake = None
    ultrasonic = None
    
    try:
        # 1. 하드웨어 및 로직 객체 초기화
        state_machine = SafetyStateMachine(ride_id="INTEG_TEST_01")
        brake = BrakeController(ride_id="INTEG_TEST_01")
        ultrasonic = UltrasonicSensor()
        
        print("\n[READY] 모든 시스템 초기화 완료!")
        print("2초 후 실시간 감시를 시작합니다. 초음파 센서 앞에 손을 댔다 떼보세요.")
        print("-" * 60)
        time.sleep(2)

        # 2. 실시간 제어 루프 (약 10Hz 속도로 구동)
        while True:
            # --- [STEP 1: 입력 (눈/귀)] ---
            distance = ultrasonic.get_distance(ride_id="INTEG_TEST_01") 
            
            if distance == float('inf'):
                print("[입력] ⚠️ 측정 범위 초과 또는 센서 방어 로직 작동 (거리: inf)")
            else:
                print(f"[입력] 물리적 거리: {distance:.2f} cm")

            # --- [STEP 2: 판단 (두뇌)] ---
            # 센서 데이터를 상태 기계가 읽을 수 있도록 포장
            sensor_data = {
                "distance_cm": distance,
            }
            
            # 상태 기계가 우선순위 규칙에 따라 제동 레벨을 결정
            brake_level, reason, conf = state_machine.evaluate(sensor_data)

            # --- [STEP 3: 출력 (팔/다리)] ---
            # 결정된 레벨에 따라 서보 모터 물리적 회전
            brake.execute_brake(level=brake_level, reason=reason, confidence=conf)

            # 메인 스레드 부하 방지 및 센서 측정 주기 조절 (0.1초)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[사용자 중단] 테스트를 안전하게 종료합니다.")
    except Exception as e:
        print(f"\n[시스템 에러] {e}")
        traceback.print_exc()
    finally:
        # 3. 종료 시 시스템 자원(GPIO, PWM) 완전 해제
        print("\n[CLEANUP] 하드웨어 자원을 해제합니다...")
        if brake:
            brake.cleanup()
        if ultrasonic:
            ultrasonic.cleanup()
        print("시스템이 완벽하게 종료되었습니다.")

if __name__ == "__main__":
    run_integration_test()