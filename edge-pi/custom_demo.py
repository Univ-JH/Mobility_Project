import asyncio
import lgpio
import time

# 기존 모듈 임포트
from src.communication.ble_manager import HelmetBLEManager
from src.control.servo_control import BrakeController
from src.control.led_warning import RearApproachLED
from src.control.control_config import REAR_LED_PIN

async def run_custom_demo():
    print("🎬 [맞춤형 데모] 스마트 자전거 안전 시스템 가동")
    print("   - 🟡 노랑: 헬멧 미착용 (브레이크 해제)")
    print("   - 🟢 초록: 헬멧 착용 & 정상 주행 / 급가속 포함 (브레이크 해제)")
    print("   - 🟣 보라 (+후방 점등): 급감속 (브레이크 해제)")
    print("   - 🔴 빨강 (+후방 점등): 사고 및 전도 (5초 유지 후 복귀)\n")
    
    ble = HelmetBLEManager()
    brake = BrakeController()
    led = RearApproachLED()
    
    asyncio.create_task(ble.start_listening())
    print("🚨 헬멧의 전원을 켜고 블루투스 연결을 기다려주세요... (종료: Ctrl+C)")
    
    last_state = None
    accident_recovery_start = 0  # ✨ 5초 복구 대기를 위한 타이머 변수

    try:
        while True:
            if not ble.is_connected:
                if last_state != "DISCONNECTED":
                    print("📡 헬멧을 찾는 중입니다... (연결 대기)")
                    led.clear()            
                    brake.release_brake()  
                    last_state = "DISCONNECTED"
                    accident_recovery_start = 0  # 끊기면 타이머도 초기화
            else:
                data = ble.last_parsed_data
                is_worn = data.get("is_worn", False)
                is_accident = data.get("is_accident", False)
                event_label = data.get("event_label", 0)
                
                # 현재 헬멧이 전도/사고 상태인지 하나로 묶어서 판단
                current_is_accident = is_accident or (event_label == 1)
                
                # ----------------------------------------------------
                # [상황 1] 사고 또는 전도 발생 (가장 최우선)
                # ----------------------------------------------------
                if current_is_accident:
                    accident_recovery_start = 0  # 사고 중에는 복구 타이머 초기화
                    if last_state != "ACCIDENT":
                        print("\n💥 [위험] 사고/전도 감지! ➔ 전/후방 빨강 점등 & 급브레이크!")
                        led._set_rgb_color(100, 0, 0)
                        lgpio.gpio_write(led.h, REAR_LED_PIN, 1)
                        brake.pull_brake()
                        last_state = "ACCIDENT"
                        
                # ----------------------------------------------------
                # [상황 1-1] 사고 상황 종료 ➔ 5초 안전 대기 로직
                # ----------------------------------------------------
                else:
                    # 방금 전까지 사고 상태였는데 정상 신호가 들어오기 시작했다면
                    if last_state == "ACCIDENT":
                        if accident_recovery_start == 0:
                            print("\n⏳ [안내] 헬멧이 정상 상태로 돌아왔습니다. 안전을 위해 5초 유지 후 복귀합니다...")
                            accident_recovery_start = time.time()
                            
                        # 아직 5초가 안 지났다면 하단 로직 스킵 (사고 상태 유지)
                        if time.time() - accident_recovery_start < 5.0:
                            pass 
                        # 5초가 다 지났다면 복구 시작!
                        else:
                            print("\n✅ 5초 경과! 현재 상태를 다시 파악하여 시스템을 복구합니다.")
                            accident_recovery_start = 0
                            last_state = "RECOVERING"  # 하단의 정상 로직이 돌도록 상태를 강제로 바꿈
                            
                    # ----------------------------------------------------
                    # 사고 대기 중(5초 이내)이 아닐 때만 아래 로직 실행
                    # ----------------------------------------------------
                    if last_state != "ACCIDENT":
                        
                        # [상황 2] 급감속 (급가속은 무시)
                        if event_label == 3:
                            if last_state != "SUDDEN_DECEL":
                                print("\n🚀 [경고] 급감속 감지! ➔ 전방 보라색 & 후방 빨강 점등 (브레이크 놔둠)")
                                led._set_rgb_color(100, 0, 100)
                                lgpio.gpio_write(led.h, REAR_LED_PIN, 1)
                                brake.release_brake()
                                last_state = "SUDDEN_DECEL"

                        # [상황 3] 헬멧 미착용
                        elif not is_worn:
                            if last_state != "UNWORN":
                                print("\n⚠️ [안내] 헬멧 미착용 ➔ 전방 노란색 점등 (브레이크 놔둠)")
                                led._set_rgb_color(100, 60, 0)
                                lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                                brake.release_brake()
                                last_state = "UNWORN"

                        # [상황 4] 헬멧 정상 착용 (급가속 포함)
                        else:
                            if last_state != "NORMAL":
                                print("\n🟢 [정상] 헬멧 착용 완료 ➔ 전방 초록색 점등 (브레이크 놔둠)")
                                led._set_rgb_color(0, 100, 0)
                                lgpio.gpio_write(led.h, REAR_LED_PIN, 0)
                                brake.release_brake()
                                last_state = "NORMAL"

            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        pass
    finally:
        print("\n🧹 시스템 안전 종료 중 (LED 및 서보모터 초기화)...")
        brake.release_brake()
        brake.cleanup()
        led.clear()   # ✨ 여기서 LED가 완전히 다 꺼집니다
        led.cleanup() 
        await ble.stop()
        print("🛑 완료되었습니다!")

if __name__ == "__main__":
    try:
        asyncio.run(run_custom_demo())
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")