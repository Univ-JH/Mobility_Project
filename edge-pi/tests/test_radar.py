"""
mmWave 레이더 센서 모듈 테스트 (거리/핀별 상세 감지)
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.control.control_config import RADAR_CR_PIN, RADAR_DT_PIN

MONITOR_SEC = 20  # 테스트 시간 20초로 연장

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
    print("\n[2] 웜업 억제 검증")
    result = sensor.check_rear_approach()
    print(f"  웜업 직후 감지값: {result}  (False 이어야 함)")
    if not result:
        print("  PASS — 웜업 억제 정상")
    else:
        print("  FAIL — 웜업 중 감지 출력 (오감지 위험)")

def test_realtime_monitor(sensor):
    print(f"\n[3] 실시간 거리별 감지 모니터링 ({MONITOR_SEC}초)")
    print("  ➔ 멀리서부터 레이더 쪽으로 천천히 다가와 보세요!")
    time.sleep(2.1) 

    detected_count = 0
    start = time.time()
    
    while time.time() - start < MONITOR_SEC:
        if hasattr(sensor, 'get_detailed_status'):
            cr_on, dt_on = sensor.get_detailed_status()
            
            if cr_on and dt_on:
                status = "🔴 [매우 근접] CR + DT 동시 감지!!"
            elif dt_on:
                status = "🟡 [원거리 접근] DT 핀에서 먼저 감지!"
            elif cr_on:
                status = "🟠 [초근접] CR 핀만 감지 중!"
            else:
                status = "🟢 이상 없음 (감지 안 됨)"
            
            if cr_on or dt_on:
                detected_count += 1
        else:
            # 예비용 코드
            approach = sensor.check_rear_approach()
            status = "🔴 접근 감지" if approach else "🟢 이상 없음"
            if approach:
                detected_count += 1

        # 터미널 창에 이전 줄을 덮어쓰며 실시간 출력
        print(f"\r  {status:<30} (경과: {time.time()-start:.1f}s)   ", end="", flush=True)
        time.sleep(0.2)

    print(f"\n\n  총 감지 횟수: {detected_count}회")
    if detected_count > 0:
        print("  PASS — 접근 감지 이벤트 발생")
    else:
        print("  INFO — 감지 없음")

def main():
    print("=" * 50)
    print("mmWave 레이더 센서 거리 확장 모듈 테스트")
    print("=" * 50)
    sensor = test_gpio_init()
    if sensor:
        test_warmup_suppression(sensor)
        test_realtime_monitor(sensor)
        sensor.cleanup()

if __name__ == "__main__":
    main()