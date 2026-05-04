import time
from src.control.servo_control import BrakeController

def run_test():
    try:
        # 컨트롤러 생성 (자동으로 level_0 셋팅됨)
        brake = BrakeController(ride_id="TEST_001")
        print("모터 테스트를 시작합니다. 3초 대기...")
        time.sleep(3)

        # 테스트 1: 약한 제동
        print("\n--- [TEST] 약한 제동 (Level 1) ---")
        brake.execute_brake("level_1", reason="Manual Test Level 1")
        time.sleep(2)

        # 테스트 2: 긴급 제동
        print("\n--- [TEST] 긴급 제동 (Level Emergency) ---")
        brake.execute_brake("level_emergency", reason="Manual Test Emergency")
        time.sleep(2)

        # 테스트 3: 브레이크 해제
        print("\n--- [TEST] 브레이크 해제 ---")
        brake.release_brake(reason="Test finished")
        time.sleep(2)

    except KeyboardInterrupt:
        print("\n[사용자 중단] 테스트를 종료합니다.")
    except Exception as e:
        print(f"\n[오류 발생] {e}")
    finally:
        # 종료 전 안전하게 모터 정지
        if 'brake' in locals():
            brake.cleanup()

if __name__ == "__main__":
    run_test()