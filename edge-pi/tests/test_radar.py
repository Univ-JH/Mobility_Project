import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MONITOR_SEC = 30

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 최종 완성 테스트 (노이즈 필터링 적용)")
    print("=" * 60)
    
    try:
        from src.control.radar import MmwaveRadarSensor
        sensor = MmwaveRadarSensor()
        if not sensor.bus:
            return
    except Exception as e:
        print(f"  FAIL — 에러: {e}")
        return

    print(f"\n[테스트 시작] {MONITOR_SEC}초 동안 진행됩니다.")
    print("🚨 [중요] 레이더가 허공(천장이나 빈 벽)을 보게 돌려놓고 멀리 떨어지세요!\n")
    time.sleep(2.0)
    
    start = time.time()
    try:
        while time.time() - start < MONITOR_SEC:
            is_detected = sensor.check_rear_approach()
            
            if is_detected:
                mark = "🔴 [경고] 묵직한 물체 접근 감지!!"
            else:
                mark = "🟢 [안전] 아무도 없음 (또는 미세 노이즈 무시 중)"
            
            print(f"\r  상태: {mark:<35} (남은시간: {MONITOR_SEC - int(time.time()-start)}초)     ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
        
    print("\n\n🛑 테스트 종료")
    sensor.cleanup()

if __name__ == "__main__":
    main()