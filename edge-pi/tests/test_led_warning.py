"""
전방 RGB LED 및 후방 레드바 경고등 모듈 통합 테스트
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN

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
        print(f"  PASS — 전후방 핀 초기화 성공")
        return led
    except Exception as e:
        print(f"  FAIL — 초기화 실패: {e}")
        return None

def test_warn_clear_cycle(led):
    print("\n[2] 경고 점등/소등 사이클")
    try:
        assert not led._active, "초기 상태가 소등이어야 함"
        print("  초기 상태: 소등  ✅")

        led.warn_rear()
        assert led._active, "warn_rear() 후 _active=True이어야 함"
        print("  warn_rear() → 빨간색 점등 + 후방 레드바 ON ✅  (육안 확인 요망)")
        time.sleep(2.0)

        led.clear()
        assert not led._active, "clear() 후 _active=False이어야 함"
        print("  clear() → 모두 소등  ✅  (육안 확인 요망)")
        print("  PASS — 점등/소등 사이클")
    except AssertionError as e:
        print(f"  FAIL — {e}")

def test_duplicate_call_guard(led):
    print("\n[3] 중복 호출 방어 검증")
    led.warn_rear()
    state_before = led._active
    led.warn_rear() 
    state_after = led._active
    if state_before == state_after:
        print("  PASS — 중복 warn_rear() 무시")
    else:
        print("  FAIL — 중복 호출로 상태 변경됨")

    led.clear()
    state_before = led._active
    led.clear() 
    state_after = led._active
    if state_before == state_after:
        print("  PASS — 중복 clear() 무시")
    else:
        print("  FAIL — 중복 호출로 상태 변경됨")

def test_various_colors(led):
    print("\n[4] 전방 다양한 색상 표출 테스트 (사용자 확인용)")
    led.test_colors()
    print("  PASS — 색상 테스트 완료")

def main():
    print("=" * 50)
    print("전후방 경고등 모듈 테스트 시작")
    print("=" * 50)
    led = test_gpio_init()
    if led:
        test_warn_clear_cycle(led)
        test_duplicate_call_guard(led)
        test_various_colors(led) # 다른 색 확인
        led.cleanup()

if __name__ == "__main__":
    main()