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
    print("   - 🔴 빨강 (+후방 점등): 사고 및 전도 (긴급 제동)\n")
    
    # 모듈 초기화
    ble = HelmetBLEManager()
    brake = BrakeController()
    led = RearApproachLED()
    
    # BLE 수신 백그라운드 실행
    asyncio.create_task(ble.start_listening())
    
    print("🚨 헬멧의 전원을 켜고 블루투스 연결을 기다려주세요... (종료: Ctrl+C)")
    
    last_state = None

    try:
        while True:
            # 헬멧과 연결이 안 되어 있을 때
            if not ble.is_connected:
                if last_state != "DISCONNECTED":
                    print("📡 헬멧을 찾는 중입니다... (연결 대기)")
                    led.clear()            
                    brake.release_brake()  
                    last_state = "DISCONNECTED"
            else:
                data = ble.last_parsed_data
                is_worn = data.get("is_worn", False)
                is_accident = data.get("is_accident", False)
                event_label = data.get("event_label", 0)
                
                # ----------------------------------------------------
                # [상황 1] 사고 또는 전도 (가장 최우선)
                # 💡 event_label == 1 이 아두이노의 '전도' 신호라고 가정
                # ----------------------------------------------------
                if is_accident or event_label == 1:
                    if last_state != "ACCIDENT":
                        print("\n💥 [위험] 사고/전도 감지! ➔ 전/후방 빨강 점등 & 급브레이크!")
                        led._set_rgb_color(100, 0, 0)             # 전방 빨강
                        lgpio.gpio_write(led.h, REAR_LED_PIN, 1)  # 후방 빨강 켜기
                        brake.pull_brake()                        # 모터 당김 (제동)
                        last_state = "ACCIDENT"

                # ----------------------------------------------------
                # [상황 2] 급감속 (💡 급가속은 무시하고 LED를 켜지 않습니다)
                # 💡 event_label == 3 이 아두이노의 '급감속' 신호라고 가정
                # ----------------------------------------------------
                elif event_label == 3:
                    if last_state != "SUDDEN_DECEL":
                        print("\n🚀 [경고] 급감속 감지! ➔ 전방 보라색 & 후방 빨강 점등 (브레이크 놔둠)")
                        led._set_rgb_color(100, 0, 100)           # 전방 보라색
                        lgpio.gpio_write(led.h, REAR_LED_PIN, 1)  # 후방 빨강 켜기
                        brake.release_brake()                     # 브레이크 안 잡음
                        last_state = "SUDDEN_DECEL"

                # ----------------------------------------------------
                # [상황 3] 헬멧 미착용
                # ----------------------------------------------------
                elif not is_worn:
                    if last_state != "UNWORN":
                        print("\n⚠️ [안내] 헬멧 미착용 ➔ 전방 노란색 점등 (브레이크 놔둠)")
                        led._set_rgb_color(100, 60, 0)            # 전방 노란색
                        lgpio.gpio_write(led.h, REAR_LED_PIN, 0)  # 후방 끄기
                        brake.release_brake()                     # 브레이크 안 잡음
                        last_state = "UNWORN"

                # ----------------------------------------------------
                # [상황 4] 헬멧 정상 착용 (안전 주행 & 급가속 포함)
                # 💡 급가속(event_label == 2)이 들어와도 이 부분으로 빠져서
                #    LED가 초록색으로 켜지거나 유지되며 경고등이 울리지 않습니다.
                # ----------------------------------------------------
                else:
                    if last_state != "NORMAL":
                        print("\n🟢 [정상] 헬멧 착용 완료 ➔ 전방 초록색 점등 (브레이크 놔둠)")
                        led._set_rgb_color(0, 100, 0)             # 전방 초록색
                        lgpio.gpio_write(led.h, REAR_LED_PIN, 0)  # 후방 끄기
                        brake.release_brake()                     # 브레이크 스르륵 풀려 있음
                        last_state = "NORMAL"

            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        pass
    finally:
        print("\n🧹 시스템 안전 종료 중...")
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