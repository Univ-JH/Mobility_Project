"""
mmWave 레이더 센서 모듈 테스트
- GPIO 칩 초기화
- CR(근거리)/DT(원거리) 핀 상태 읽기
- 10초간 실시간 감지 모니터링

실행: python -m tests.test_radar  (edge-pi/ 루트에서, 라즈베리파이 필수)
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.control_config import RADAR_CR_PIN, RADAR_DT_PIN

MONITOR_SEC = 10


def test_gpio_init():
    print("\n[1] GPIO 초기화")
    try:
        import lgpio
    except ImportError:
        print("  [SKIP] lgpio 미설치 — 라즈베리파이에서 실행 필요")
        return None

    try:
        from src.control.radar import MmwaveRadarSensor
        sensor = MmwaveRadarSensor()
        print(f"  PASS — CR핀={RADAR_CR_PIN}, DT핀={RADAR_DT_PIN} 초기화 성공")
        return sensor
    except Exception as e:
        print(f"  FAIL — 초기화 실패: {e}")
        return None


def test_warmup_suppression(sensor):
    """웜업 중 False 반환 검증"""
    print("\n[2] 웜업 억제 검증")
    # _ready_at이 아직 미래인 경우 check_rear_approach()는 반드시 False
    result = sensor.check_rear_approach()
    print(f"  웜업 직후 감지값: {result}  (False 이어야 함)")
    if not result:
        print("  PASS — 웜업 억제 정상")
    else:
        print("  FAIL — 웜업 중 감지 출력 (오감지 위험)")


def test_realtime_monitor(sensor):
    print(f"\n[3] 실시간 감지 모니터링 ({MONITOR_SEC}초) — 레이더 앞에 손을 가져다 대보세요")
    time.sleep(2.1)  # 웜업 대기

    detected_count = 0
    start = time.time()
    while time.time() - start < MONITOR_SEC:
        approach = sensor.check_rear_approach()
        status = "🔴 접근 감지" if approach else "🟢 이상 없음"
        print(f"\r  {status}  (경과: {time.time()-start:.1f}s)", end="", flush=True)
        if approach:
            detected_count += 1
        time.sleep(0.2)

    print(f"\n  감지 횟수: {detected_count}회 / {int(MONITOR_SEC/0.2)}샘플")
    if detected_count > 0:
        print("  PASS — 접근 감지 이벤트 발생")
    else:
        print("  INFO — 감지 없음 (레이더 앞 물체 없음 — 수동 확인 필요)")


def main():
    print("=" * 50)
    print("mmWave 레이더 센서 모듈 테스트")
    print("=" * 50)
    sensor = test_gpio_init()
    if sensor:
        test_warmup_suppression(sensor)
        test_realtime_monitor(sensor)
        sensor.cleanup()


if __name__ == "__main__":
    main()
