import asyncio
import lgpio
import time

from src.communication.ble_manager import HelmetBLEManager
from src.control.servo_control import BrakeController
from src.control.led_warning import RearApproachLED
from src.control.control_config import REAR_LED_PIN

async def run_custom_demo():
    print("🎬 [맞춤형 데모] 스마트 자전거 안전 시스템 가동")
    print("   - 🟡 헬멧 미착용: 전방 노랑 / 후방 꺼짐")
    print("   - 🟢 헬멧 착용 (급가속 포함): 전방 초록 / 후방 꺼짐")
    print("   - 🔴 급감속: 전방 빨강 / 후방 빨강 반짝반짝 (5초간 홀딩)")
    print("   - 🔴 사고 및 전도: 전방 빨강 / 후방 빨강 켜짐 (5초간 홀딩)\n")
    
    ble = HelmetBLEManager()
    brake = BrakeController()
    led = RearApproachLED()
    
    asyncio.create_task(ble.start_listening())
    print("🚨 헬멧의 전원을 켜고 블루투스 연결을 기다려주세요... (종료: Ctrl+C)")
    
    last_base_state = None
    locked_state = None
    event_lock_time = 0
    
    ignore_accident_until_clear = False
    ignore_decel_until_clear = False

    try:
        while True:
            if not ble.is_connected:
                if last_base_state != "DISCONNECTED":
                    print("📡 헬멧을 찾는 중입니다... (연결 대기)")
                    led.clear()            
                    brake.release_brake()  
                    last_base_state = "DISCONNECTED"
                    locked_state = None
                    ignore_accident_until_clear = False
                    ignore_decel_until_clear = False
            else:
                data = ble.last_parsed_data
                is_worn = data.get("is_worn", False)
                is_accident = data.get("is_accident", False)
                event_label = data.get("event_label", 0)
                
                current_time = time.time()

                # 버그 방어: 아두이노 급가속(2) 시 빨간불 오작동 방지
                if event_label == 2:
                    is_accident = False 

                # 아두이노 센서가 0으로 정상화되면 무시 모드 해제
                if event_label == 0 and not is_accident:
                    ignore_accident_until_clear = False
                    ignore_decel_until_clear = False

                # ====================================================
                # 1. 시간이 지나면 푸는 로직 (5초 홀딩 종료)
                # ====================================================
                if locked_state is not None:
                    if current_time - event_lock_time >= 5.0:
                        # 5초가 지나면 락을 풀고, 아두이노의 잔여 신호는 0이 될 때까지 무시함
                        if locked_state == "ACCIDENT":
                            ignore_accident_until_clear = True
                        elif locked_state == "SUDDEN_DECEL":
                            ignore_decel_until_clear = True
                            
                        locked_state = None
                        last_base_state = None 
                        print("\n🔓 [안내] 5초 홀딩 종료! 다시 신호를 잡아 상태를 정합니다.")

                # ====================================================
                # 2. 처음 주요 이벤트 신호를 받았을 때 (5초 홀딩 시작)
                # ====================================================
                if locked_state is None:
                    if (is_accident or event_label == 1) and not ignore_accident_until_clear:
                        print("\n💥 [위험] 전도/사고 감지! ➔ 처음 신호부터 5초간 홀딩합니다.")
                        locked_state = "ACCIDENT"
                        event_lock_time = current_time
                        
                    elif event_label == 3 and not ignore_decel_until_clear:
                        print("\n🚨 [경고] 급감속 감지! ➔ 처음 신호부터 5초간 홀딩합니다.")
                        locked_state = "SUDDEN_DECEL"
                        event_lock_time = current_time

                # ====================================================
                # 3. 확정된 상태에 따른 LED & 모터 동작
                # ====================================================
                if locked_state == "ACCIDENT":
                    led._set_rgb_color(100, 0, 0)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, 1)
                    brake.pull_brake()
                    
                elif locked_state == "SUDDEN_DECEL":
                    led._set_rgb_color(100, 0, 0)
                    blink_on = int((current_time * 5) % 2)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, blink_on)
                    brake.release_brake() 
                    
                else:
                    # ====================================================
                    # 4. 이벤트 안 받으면 그냥 계속 진행하는 로직
                    # ====================================================
                    if not is_worn:
                        if last_base_state != "UNWORN":
                            print("\n⚠️ [안내] 헬멧 미착용 ➔ 전방 노랑 / 후방 꺼짐")
                            led._set_rgb_color(100, 60, 0)
                            lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                            brake.release_brake()
                            last_base_state = "UNWORN"
                            
                    else:
                        if last_base_state != "NORMAL":
                            print("\n🟢 [정상] 헬멧 착용 중 ➔ 전방 초록 / 후방 꺼짐")
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