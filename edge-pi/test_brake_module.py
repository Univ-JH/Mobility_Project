import time

from src.control.servo_control import BrakeController

def run_test():
    
    # 1. 브레이크 컨트롤러 객체 생성 (자동으로 초기화 및 0도 세팅됨)
    brake = BrakeController()
    time.sleep(1) # 초기 안정화 대기

    try:
        # [테스트 1] 180도로 이동 (완전 잠금)
        print("\n▶️ [STEP 1] 180도로 이동합니다. (브레이크 잠금)")
        brake.pull_brake()  # 또는 brake.set_angle(180)
        time.sleep(2.0)     # 2초 대기

        # [테스트 2] 0도로 이동 (완전 해제)
        print("\n▶️ [STEP 2] 0도로 이동합니다. (브레이크 해제)")
        brake.release_brake() # 또는 brake.set_angle(0)
        time.sleep(2.0)       # 2초 대기

        # [테스트 3] 90도로 이동 (중간 위치)
        print("\n▶️ [STEP 3] 90도로 이동합니다. (중간 확인)")
        brake.set_angle(90)
        time.sleep(2.0)       # 2초 대기
        
        print("\n✅ 모든 동작 테스트가 성공적으로 완료되었습니다!")

    except KeyboardInterrupt:
        print("\n[사용자 중단] 테스트를 강제 종료합니다.")
    except Exception as e:
        print(f"\n[시스템 에러] {e}")
    finally:
        # 3. 종료 시 안전하게 리소스 반환
        brake.cleanup()

if __name__ == "__main__":
    run_test()