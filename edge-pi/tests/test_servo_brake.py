"""
서보 브레이크 모듈 테스트
- GPIO 초기화
- 브레이크 해제(110도) → 작동(30도) → 해제 사이클
- 각도 및 PWM 듀티 계산값 검증

실행: python -m tests.test_servo_brake  (edge-pi/ 루트에서, 라즈베리파이 필수)
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.control_config import (
    SERVO_PIN, PWM_FREQ,
    SERVO_MIN_PULSE, SERVO_MAX_PULSE,
    BRAKE_RELEASE_ANGLE, BRAKE_PULL_ANGLE,
    BRAKE_HOLD_TIME,
)


def test_duty_calculation():
    """하드웨어 없이 듀티 계산 로직만 검증"""
    print("\n[1] PWM 듀티 계산 검증 (하드웨어 불필요)")

    def calc_duty(angle):
        if angle < 0: angle = 0
        if angle > 180: angle = 180
        pw = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        return (pw / 20000.0) * 100.0

    cases = [
        (0,   SERVO_MIN_PULSE),
        (180, SERVO_MAX_PULSE),
        (BRAKE_RELEASE_ANGLE, None),
        (BRAKE_PULL_ANGLE,    None),
    ]
    all_pass = True
    for angle, expected_pw in cases:
        duty = calc_duty(angle)
        pw   = SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)
        if expected_pw and abs(pw - expected_pw) > 1:
            print(f"  FAIL — {angle}도: pw={pw:.1f} (기대 {expected_pw})")
            all_pass = False
        else:
            print(f"  {angle:3d}도 → pw={pw:.0f}µs  duty={duty:.2f}%  OK")

    print(f"  {'PASS' if all_pass else 'FAIL'} — 듀티 계산")
    return all_pass


def test_gpio_brake_cycle():
    """실제 GPIO 브레이크 동작 사이클 (라즈베리파이 전용)"""
    print("\n[2] GPIO 브레이크 사이클 (해제→작동→해제)")

    try:
        import lgpio
    except ImportError:
        print("  [SKIP] lgpio 미설치 — 라즈베리파이에서 실행 필요")
        return

    try:
        from src.control.servo_control import BrakeController
        ctrl = BrakeController()
    except Exception as e:
        print(f"  FAIL — BrakeController 초기화 실패: {e}")
        return

    try:
        print(f"  브레이크 해제 ({BRAKE_RELEASE_ANGLE}도)")
        ctrl.release_brake()
        assert ctrl.current_angle == BRAKE_RELEASE_ANGLE, "해제 각도 불일치"
        print(f"  현재 각도: {ctrl.current_angle}도  ✅")

        time.sleep(1.0)

        print(f"  브레이크 작동 ({BRAKE_PULL_ANGLE}도)")
        ctrl.pull_brake()
        assert ctrl.current_angle == BRAKE_PULL_ANGLE, "제동 각도 불일치"
        print(f"  현재 각도: {ctrl.current_angle}도  ✅")

        time.sleep(1.0)

        print(f"  브레이크 재해제 ({BRAKE_RELEASE_ANGLE}도)")
        ctrl.release_brake()
        assert ctrl.current_angle == BRAKE_RELEASE_ANGLE, "재해제 각도 불일치"
        print(f"  현재 각도: {ctrl.current_angle}도  ✅")

        print("  PASS — 브레이크 사이클 완료")

    except AssertionError as e:
        print(f"  FAIL — {e}")
    finally:
        ctrl.cleanup()


def main():
    print("=" * 50)
    print("서보 브레이크 모듈 테스트")
    print("=" * 50)
    test_duty_calculation()
    test_gpio_brake_cycle()


if __name__ == "__main__":
    main()
