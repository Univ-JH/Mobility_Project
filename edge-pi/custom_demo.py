import asyncio
import lgpio
import time

from src.communication.ble_manager import HelmetBLEManager
from src.control.servo_control import BrakeController
from src.control.led_warning import RearApproachLED
from src.control.control_config import REAR_LED_PIN

async def run_custom_demo():
    print("🎬 [맞춤형 데모] 스마트 자전거 안전 시스템 가동")
    print("   - 🟡 헬멧 미착용: 전방 노랑 / 후방 꺼짐 (X)")
    print("   - 🟢 헬멧 착용 (급가속 포함): 전방 초록 / 후방 꺼짐 (X)")
    print("   - 🔴 급감속: 전방 빨강 / 후방 빨강 반짝반짝 (3초간 락온)")
    print("   - 🔴 사고 및 전도: 전방 빨강 / 후방 빨강 켜짐 (3초간 락온)\n")
    
    ble = HelmetBLEManager()
    brake = BrakeController()
    led = RearApproachLED()
    
    asyncio.create_task(ble.start_listening())
    print("🚨 헬멧의 전원을 켜고 블루투스 연결을 기다려주세요... (종료: Ctrl+C)")
    
    last_base_state = None
    locked_state = None
    event_lock_time = 0

    try:
        while True:
            if not ble.is_connected:
                if last_base_state != "DISCONNECTED":
                    print("📡 헬멧을 찾는 중입니다... (연결 대기)")
                    led.clear()            
                    brake.release_brake()  
                    last_base_state = "DISCONNECTED"
                    locked_state = None
            else:
                data = ble.last_parsed_data
                is_worn = data.get("is_worn", False)
                is_accident = data.get("is_accident", False)
                event_label = data.get("event_label", 0)
                
                current_time = time.time()
                
                # ====================================================
                # 1. 상태 갱신 루틴 (3초마다 잠금 해제 및 재파악)
                # ====================================================
                if locked_state is not None:
                    if current_time - event_lock_time >= 3.0:
                        # 3초가 지났으므로 강제 잠금을 풉니다.
                        # 직후 아래의 로직을 타고 현재 센서값에 맞춰 원래대로 돌아가거나 갱신됩니다.
                        locked_state = None
                        last_base_state = None 

                # ====================================================
                # 2. 위험 감지 시 3초 타이머 시작 (락온)
                # ====================================================
                if locked_state is None:
                    if is_accident or event_label == 1:
                        print("\n💥 [위험] 전도/사고 감지! ➔ 3초간 빨강/빨강 유지")
                        locked_state = "ACCIDENT"
                        event_lock_time = current_time
                        
                    elif event_label == 3:
                        print("\n🚨 [경고] 급감속 감지! ➔ 3초간 빨강/반짝반짝 유지")
                        locked_state = "SUDDEN_DECEL"
                        event_lock_time = current_time

                # ====================================================
                # 3. 확정된 상태에 따른 LED & 모터 동작
                # ====================================================
                if locked_state == "ACCIDENT":
                    # [전도] 전방 빨강, 후방 빨강 고정, 긴급 제동
                    led._set_rgb_color(100, 0, 0)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, 1)
                    brake.pull_brake()
                    
                elif locked_state == "SUDDEN_DECEL":
                    # [급감속] 전방 빨강, 후방 빨강 반짝반짝, 브레이크 해제
                    led._set_rgb_color(100, 0, 0)
                    
                    # ✨ 0.2초 간격으로 1과 0을 오가는 반짝반짝 알고리즘
                    blink_on = int((current_time * 5) % 2)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, blink_on)
                    
                    brake.release_brake() 
                    
                else:
                    # 잠금 상태가 아닐 때 = 헬멧을 평범하게 썼다 벗었다 하는 상태
                    if not is_worn:
                        # [미착용] 전방 노랑, 후방 X
                        if last_base_state != "UNWORN":
                            print("\n⚠️ [안내] 헬멧 미착용 ➔ 원래대로 복귀 (전방 노랑)")
                            led._set_rgb_color(100, 60, 0)
                            lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                            brake.release_brake()
                            last_base_state = "UNWORN"
                            
                    else:
                        # [착용] 전방 초록, 후방 X (급가속(event_label == 2)도 무시하고 이쪽으로 빠짐)
                        if last_base_state != "NORMAL":
                            print("\n🟢 [정상] 헬멧 착용 확인 ➔ 원래대로 복귀 (전방 초록)")
                            led._set_rgb_color(0, 100, 0)
                            lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                            brake.release_brake()
                            last_base_state = "NORMAL"

            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        pass
    finally:
        print("\n🧹 시스템 안전 종료 중 (초기화)...")
        brake.release_brake()
        brake.cleanup()
        led.clear()
        led.cleanup()
        await ble.stop()
        print("🛑 완료되었습니다!")

if __name__ == "__main__":
    try:
        asyncio.run(run_custom_demo())
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")