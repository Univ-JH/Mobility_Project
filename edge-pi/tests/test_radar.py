"""
mmWave 레이더 센서 순수 전기 신호(RAW) 분석 테스트
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MONITOR_SEC = 30  # 충분한 테스트를 위해 30초로 세팅

def test_gpio_init():
    print("\n[1] GPIO 초기화 및 핀 연결 확인")
    try:
        from src.control.radar import MmwaveRadarSensor
        sensor = MmwaveRadarSensor()
        return sensor
    except Exception as e:
        print(f"  FAIL — 초기화 실패: {e}")
        return None

def test_raw_monitor(sensor):
    print(f"\n[2] ⚡ 순수 전기 신호(RAW DATA) 실시간 모니터링 ({MONITOR_SEC}초)")
    print("🚨 [매우 중요] 레이더는 키보드 치는 손가락이나 숨쉬는 가슴팍 움직임까지 잡아냅니다.")
    print("🚨 테스트를 실행하자마자 센서 방향에서 아예 피해서 2미터 이상 떨어지세요!\n")
    time.sleep(2.1)
    
    start = time.time()
    while time.time() - start < MONITOR_SEC:
        cr_val, dt_val = sensor.get_raw_status()
        
        # 가시성을 높이기 위한 신호 표시기
        cr_mark = "🔴 (신호 들어옴)" if cr_val == 1 else "⚪ (신호 없음)"
        dt_mark = "🔴 (신호 들어옴)" if dt_val == 1 else "⚪ (신호 없음)"
        
        print(f"\r  [RAW] CR(핀4): {cr_val} {cr_mark} | DT(핀27): {dt_val} {dt_mark}  (남은시간: {MONITOR_SEC - int(time.time()-start)}초)   ", end="", flush=True)
        time.sleep(0.2)
    print("\n\n  모니터링 종료 완료")

def main():
    print("=" * 60)
    print("mmWave 레이더 정밀 디버깅 (전기 신호 추적)")
    print("=" * 60)
    sensor = test_gpio_init()
    if sensor:
        test_raw_monitor(sensor)
        sensor.cleanup()

if __name__ == "__main__":
    main()