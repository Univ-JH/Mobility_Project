"""
GPIO 전체 초기화 스크립트 — 메인 프로세스 비정상 종료 후 핀 상태 강제 복구용.

사용법:
    sudo python gpio_reset.py
"""

import sys
import lgpio

# BCM 핀 번호 (control_config.py 기준)
SERVO_PIN   = 18
LED_R_PIN   = 12
LED_G_PIN   = 13
LED_B_PIN   = 19
RADAR_CR_PIN = 4
RADAR_DT_PIN = 27

PWM_FREQ = 50

OUTPUT_PINS = [SERVO_PIN, LED_R_PIN, LED_G_PIN, LED_B_PIN]
INPUT_PINS  = [RADAR_CR_PIN, RADAR_DT_PIN]


def _open_chip() -> int:
    for chip in (4, 0):
        try:
            h = lgpio.gpiochip_open(chip)
            print(f"[gpio_reset] gpiochip{chip} 열기 성공")
            return h
        except lgpio.error:
            continue
    print("[gpio_reset] ERROR: gpiochip 열기 실패", file=sys.stderr)
    sys.exit(1)


def reset_all():
    h = _open_chip()
    errors = []

    # 출력 핀 — LOW 설정 후 해제
    for pin in OUTPUT_PINS:
        try:
            lgpio.gpio_claim_output(h, pin, 0)
            print(f"[gpio_reset] GPIO{pin} → LOW")
        except lgpio.error as e:
            errors.append(f"GPIO{pin} claim_output 실패: {e}")

    # 서보 PWM 명시적 정지 (duty=0)
    try:
        lgpio.tx_pwm(h, SERVO_PIN, PWM_FREQ, 0)
        print(f"[gpio_reset] GPIO{SERVO_PIN} PWM 정지")
    except lgpio.error as e:
        errors.append(f"GPIO{SERVO_PIN} PWM 정지 실패: {e}")

    # 입력 핀 — claim 후 즉시 해제 (pull-down 제거)
    for pin in INPUT_PINS:
        try:
            lgpio.gpio_claim_input(h, pin, lgpio.SET_PULL_NONE)
            print(f"[gpio_reset] GPIO{pin} pull 해제")
        except lgpio.error as e:
            errors.append(f"GPIO{pin} claim_input 실패: {e}")

    # 전체 핀 free
    for pin in OUTPUT_PINS + INPUT_PINS:
        try:
            lgpio.gpio_free(h, pin)
        except lgpio.error:
            pass

    lgpio.gpiochip_close(h)

    if errors:
        print("\n[gpio_reset] 일부 핀 처리 중 오류:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n[gpio_reset] 모든 GPIO 초기화 완료.")


if __name__ == "__main__":
    reset_all()
