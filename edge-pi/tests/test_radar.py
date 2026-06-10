import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MONITOR_SEC = 60

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 실시간 감지 최종 테스트")
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

    print(f"\n[테스트 시작] {MONITOR_SEC}초 동안 센서 앞을 움직여보세요!")
    print("💡 사람이 없을 때와 있을 때 숫자가 어떻게 변하는지 꼭 확인해주세요.\n")
    time.sleep(2.0) # 웜업 대기
    
    start = time.time()
    try:
        while time.time() - start < MONITOR_SEC:
            # 센서 데이터 읽어오기
            val = sensor.get_raw_status()
            
            if val == 0:
                mark = "⚪ (안전 / 사람 없음)"
            else:
                mark = f"🔴 [접근 감지됨!] (신호값: {val})"
            
            # 터미널 한 줄에 계속 덮어쓰기
            print(f"\r  [레이더 수신] 데이터: {val:03d} {mark}   (남은시간: {MONITOR_SEC - int(time.time()-start)}초)     ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
        
    print("\n\n🛑 테스트 종료")
    sensor.cleanup()

if __name__ == "__main__":
    main()