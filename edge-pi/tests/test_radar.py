import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MONITOR_SEC = 30

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 최종 완성 테스트 (R03 레지스터 타겟팅)")
    print("=" * 60)
    
    try:
        from src.control.radar import MmwaveRadarSensor
        sensor = MmwaveRadarSensor()
        if not sensor.bus:
            print("❌ 센서 초기화에 실패했습니다.")
            return
    except Exception as e:
        print(f"  FAIL — 에러: {e}")
        return

    print(f"\n[테스트 시작] {MONITOR_SEC}초 동안 센서 앞에서 멀어졌다 다가왔다 해보세요!")
    time.sleep(2.0)
    
    start = time.time()
    try:
        while time.time() - start < MONITOR_SEC:
            # 방금 만든 함수를 호출하여 접근 여부(True/False) 확인
            is_detected = sensor.check_rear_approach()
            
            if is_detected:
                mark = "🔴 [경고] 후방 차량/사람 접근 감지!!"
            else:
                mark = "🟢 [안전] 아무도 없음"
            
            print(f"\r  상태: {mark:<30} (남은시간: {MONITOR_SEC - int(time.time()-start)}초)     ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
        
    print("\n\n🛑 테스트 종료")
    sensor.cleanup()

if __name__ == "__main__":
    main()