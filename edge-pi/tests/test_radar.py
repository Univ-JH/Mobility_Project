import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MONITOR_SEC = 60

def main():
    print("=" * 60)
    print("📡 mmWave 레이더 I2C 실시간 감지 테스트")
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
    print("💡 멀리 떨어졌다가 가까이 다가오면서 숫자가 어떻게 변하는지 관찰하세요.\n")
    time.sleep(2.0)
    
    start = time.time()
    try:
        while time.time() - start < MONITOR_SEC:
            # I2C 데이터 읽어오기
            val = sensor.get_raw_status()
            
            # 보통 0이면 없음, 1 이상이면 감지됨
            if val == 0:
                mark = "⚪ (안전 / 사람 없음)"
            else:
                mark = f"🔴 [접근 감지됨!] (신호값: {val})"
            
            print(f"\r  [I2C 수신] 데이터: {val:03d} {mark}   (남은시간: {MONITOR_SEC - int(time.time()-start)}초)     ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
        
    print("\n\n🛑 테스트 종료")
    sensor.cleanup()

if __name__ == "__main__":
    main()