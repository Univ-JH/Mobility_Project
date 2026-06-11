import asyncio
import lgpio
import time

from src.communication.ble_manager import HelmetBLEManager
from src.control.servo_control import BrakeController
from src.control.led_warning import RearApproachLED
from src.control.control_config import REAR_LED_PIN

async def run_custom_demo():
    print("🎬 [맞춤형 데모] 스마트 자전거 안전 시스템 가동")
    print("   - 🟡 헬멧 미착용: 전방 노랑 / 후방 꺼짐 (즉각 반응)")
    print("   - 🟢 헬멧 착용 (정상, 급가속[3], 5번 무시): 전방 초록 / 후방 꺼짐 (즉각 반응)")
    print("   - 🔴 급정거 [4]: 전방 빨강 / 후방 빨강 반짝반짝 (✨ 3초 홀딩)")
    print("   - 🔴 전도[1] 및 충돌[2]: 전방 빨강 / 후방 빨강 켜짐 (✨ 3초 홀딩)\n")
    
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

                # ====================================================
                # 💡 버그 방어: 무시할 이벤트(급가속 3번, 이탈 5번) 필터링
                # 아두이노가 해당 번호를 보낼 때 is_accident를 True로 쏘는 
                # 오작동을 방지하기 위해 강제로 False로 덮어씌웁니다.
                # ====================================================
                if event_label in [3, 5]:
                    is_accident = False 

                # 아두이노 센서가 0(정상)으로 돌아오면 무시 모드 해제
                if event_label == 0 and not is_accident:
                    ignore_accident_until_clear = False
                    ignore_decel_until_clear = False

                # ====================================================
                # 1. 3초 홀딩 해제 로직
                # ====================================================
                if locked_state is not None:
                    if current_time - event_lock_time >= 3.0: 
                        if locked_state == "ACCIDENT":
                            ignore_accident_until_clear = True
                        elif locked_state == "SUDDEN_DECEL":
                            ignore_decel_until_clear = True
                            
                        locked_state = None
                        last_base_state = None 
                        print("\n🔓 [안내] 3초 홀딩 종료! 실시간 파악 모드로 복귀합니다.")

                # ====================================================
                # 2. 오직 "위험 이벤트"만 3초 홀딩 시작 (급가속 3, 이탈 5는 통과)
                # ====================================================
                if locked_state is None:
                    # 1번(전도) 또는 2번(충돌)
                    if (is_accident or event_label in [1, 2]) and not ignore_accident_until_clear:
                        event_name = "전도" if event_label == 1 else "충돌"
                        print(f"\n💥 [위험] {event_name} 감지! ➔ 3초간 화면 락온 (모터 잡음)")
                        locked_state = "ACCIDENT"
                        event_lock_time = current_time
                        
                    # 4번(급정거)
                    elif event_label == 4 and not ignore_decel_until_clear:
                        print("\n🚨 [경고] 급정거 감지! ➔ 3초간 화면 락온 (반짝반짝)")
                        locked_state = "SUDDEN_DECEL"
                        event_lock_time = current_time

                # ====================================================
                # 3. 상태 표출 (락온 상태 우선 처리, 아니면 즉각 처리)
                # ====================================================
                if locked_state == "ACCIDENT":
                    led._set_rgb_color(100, 0, 0)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, 1)
                    brake.pull_brake()
                    
                elif locked_state == "SUDDEN_DECEL":
                    led._set_rgb_color(100, 0, 0)
                    blink_on = int((current_time * 5) % 2)
                    lgpio.gpio_write(led.h, REAR_LED_PIN, blink_on)
                    brake.release_brake() # 급정거는 브레이크 풀려 있음
                    
                else:
                    # ====================================================
                    # 4. 일상 이벤트 (미착용, 정상, 3번 급가속, 5번 이탈 의심)
                    # -> 딜레이 없이 쌩쌩 돌아감
                    # ====================================================
                    if not is_worn:
                        if last_base_state != "UNWORN":
                            print("\n⚠️ [안내] 헬멧 미착용 ➔ 전방 노랑 / 후방 꺼짐 (실시간 반영)")
                            led._set_rgb_color(100, 60, 0)
                            lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                            brake.release_brake()
                            last_base_state = "UNWORN"
                            
                    else:
                        if last_base_state != "NORMAL":
                            print("\n🟢 [정상] 헬멧 착용 완료 ➔ 전방 초록 / 후방 꺼짐 (실시간 반영)")
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