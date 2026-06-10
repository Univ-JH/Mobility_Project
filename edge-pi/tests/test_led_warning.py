"""
전/후방 경고등 모듈 테스트
- GPIO 초기화 검증 (전방 RGB + 후방 레드바)
- 경고 점등 → 소등 사이클 검증
- 중복 호출 방어 로직 검증

실행: python -m tests.test_led_warning
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN

def test_gpio_init():
    print("\n[1] GPIO 초기화")
    try:
        import lgpio
    except ImportError:
        print("  [SKIP] lgpio 미설치 — 라즈베리파이에서 실행 필요")
        return None

    try:
        from src.control.led_warning import RearApproachLED
        led = RearApproachLED()
        print(f"  PASS — 전방 RGB(R={LED_R_PIN}, G={LED_G_PIN}, B={LED_B_PIN}), 후방 바({REAR_LED_PIN}) 초기화 성공")
        return led
    except Exception as e:
        print(f"  FAIL — 초기화 실패: {e}")
        return None

def test_warn_clear_cycle(led):
    print("\n[2] 경고 점등/소등 사이클")
    try:
        # 초기 상태 확인
        assert not led._active, "초기 상태가 소등이어야 함"
        print("  초기 상태: 소등  ✅")

        # 경고 점등
        led.warn_rear()
        assert led._active, "warn_rear() 후 _active=True이어야 함"
        print("  warn_rear() → 빨간 점등  ✅  (LED 육안 확인)")
        time.sleep(2.0)

        # 소등
        led.clear()
        assert not led._active, "clear() 후 _active=False이어야 함"
        print("  clear() → 소등  ✅  (LED 육안 확인)")

        print("  PASS — 점등/소등 사이클")
    except AssertionError as e:
        print(f"  FAIL — {e}")

def test_duplicate_call_guard(led):
    """중복 warn/clear 호출 시 상태 불변 검증"""
    print("\n[3] 중복 호출 방어 검증")
    
    led.warn_rear()
    state_before = led._active
    led.warn_rear()  # 중복 호출 — 상태 불변이어야 함
    state_after = led._active
    
    if state_before == state_after:
        print("  PASS — 중복 warn_rear() 안전하게 무시")
    else:
        print("  FAIL — 중복 호출로 상태 변경됨")

    led.clear()
    state_before = led._active
    led.clear()  # 중복 호출
    state_after = led._active
    
    if state_before == state_after:
        print("  PASS — 중복 clear() 안전하게 무시")
    else:
        print("  FAIL — 중복 호출로 상태 변경됨")

def main():
    print("=" * 50)
    print("전/후방 LED 경고등 모듈 통합 테스트")
    print("=" * 50)
    led = test_gpio_init()
    if led:
        test_warn_clear_cycle(led)
        test_duplicate_call_guard(led)
        led.cleanup()

if __name__ == "__main__":
    main()