"""
안전 상태 머신 모듈 테스트 (하드웨어 불필요)
- 우선순위별 센서 입력 조합 → 올바른 브레이크 레벨/이유 반환 검증
- 상태 전이 로그 출력 확인

실행: python -m tests.test_state_machine  (edge-pi/ 루트에서)
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.state.state_machine import SafetyStateMachine

RIDE_ID = "test-ride-statemachine"


def run_case(sm, label, sensor_data, exp_level, exp_state=None):
    level, reason, conf = sm.evaluate(sensor_data)
    level_ok = (level == exp_level)
    state_ok = (exp_state is None) or (sm.current_state == exp_state)
    ok = level_ok and state_ok
    status = "PASS" if ok else "FAIL"
    print(f"  {status}  [{label}]  level={level}  state={sm.current_state}  conf={conf:.2f}")
    if not ok:
        print(f"         기대: level={exp_level}  state={exp_state}")
    return ok


def test_priority_order():
    """우선순위 순서 검증 — 높은 우선순위가 낮은 우선순위를 덮어써야 함"""
    print("\n[1] 우선순위 판단 로직 검증")
    sm = SafetyStateMachine(RIDE_ID)
    all_pass = True

    cases = [
        # (설명, 센서데이터, 기대_레벨, 기대_상태)
        ("P0: 사고 감지 (최우선)",
         {"is_worn": True,  "is_accident": True,  "surface_class": "road",     "confidence": 0.9, "rear_approach": False},
         "level_emergency", "RIDER_EMERGENCY"),

        ("P0: 헬멧 미착용 (최우선)",
         {"is_worn": False, "is_accident": False, "surface_class": "road",     "confidence": 0.9, "rear_approach": False},
         "level_emergency", "RIDER_EMERGENCY"),

        ("P0 우선 > P1: 사고+후방접근",
         {"is_worn": True,  "is_accident": True,  "surface_class": "road",     "confidence": 0.9, "rear_approach": True},
         "level_emergency", "RIDER_EMERGENCY"),

        ("P1: 후방 접근 감지",
         {"is_worn": True,  "is_accident": False, "surface_class": "road",     "confidence": 0.9, "rear_approach": True},
         "level_1", "REAR_APPROACH_WARNING"),

        ("P2: 비전 신뢰도 낮음 (fail-safe)",
         {"is_worn": True,  "is_accident": False, "surface_class": "road",     "confidence": 0.3, "rear_approach": False},
         "level_1", "UNCERTAIN_ENVIRONMENT"),

        ("P3: 인도 감지 (신뢰도 충분)",
         {"is_worn": True,  "is_accident": False, "surface_class": "sidewalk", "confidence": 0.8, "rear_approach": False},
         "level_1", "ZONE_VIOLATION"),

        ("Default: 정상 주행",
         {"is_worn": True,  "is_accident": False, "surface_class": "road",     "confidence": 0.9, "rear_approach": False},
         "level_0", "NORMAL"),
    ]

    for label, data, exp_level, exp_state in cases:
        sm2 = SafetyStateMachine(RIDE_ID)  # 케이스마다 초기화
        if not run_case(sm2, label, data, exp_level, exp_state):
            all_pass = False

    print(f"  {'PASS' if all_pass else 'FAIL'} — 우선순위 전체")
    return all_pass


def test_state_transition_log():
    """동일 상태 재입력 시 로그 미출력 검증 (중복 transition 방지)"""
    print("\n[2] 상태 전이 중복 방지 검증")
    sm = SafetyStateMachine(RIDE_ID)
    normal_data = {"is_worn": True, "is_accident": False, "surface_class": "road", "confidence": 0.9, "rear_approach": False}

    sm.evaluate(normal_data)
    state_after_first = sm.current_state

    sm.evaluate(normal_data)  # 동일 입력 → 상태 변경 없어야 함
    state_after_second = sm.current_state

    if state_after_first == state_after_second == "NORMAL":
        print("  PASS — 동일 상태 중복 전이 없음")
    else:
        print(f"  FAIL — 상태 변경됨: {state_after_first} → {state_after_second}")


def test_confidence_boundary():
    """비전 신뢰도 경계값 테스트 (0.50 임계)"""
    print("\n[3] 비전 신뢰도 경계값 테스트 (임계값=0.50)")
    sm = SafetyStateMachine(RIDE_ID)
    all_pass = True

    boundary_cases = [
        (0.49, "level_1", "UNCERTAIN_ENVIRONMENT"),  # 0.49 < 0.50 → fail-safe
        (0.50, "level_0", "NORMAL"),                  # 0.50 < 0.50 → False → 정상
        (0.51, "level_0", "NORMAL"),                  # 0.51 < 0.50 → False → 정상
    ]
    # 임계 조건: conf < VISION_CONFIDENCE_THRESHOLD (0.50) → 경계값 0.50 은 정상 통과

    for conf, exp_level, exp_state in boundary_cases:
        sm2 = SafetyStateMachine(RIDE_ID)
        data = {"is_worn": True, "is_accident": False, "surface_class": "road", "confidence": conf, "rear_approach": False}
        if not run_case(sm2, f"conf={conf}", data, exp_level, exp_state):
            all_pass = False

    print(f"  {'PASS' if all_pass else 'FAIL'} — 경계값 전체")


def main():
    print("=" * 50)
    print("안전 상태 머신 모듈 테스트")
    print("=" * 50)
    test_priority_order()
    test_state_transition_log()
    test_confidence_boundary()


if __name__ == "__main__":
    main()
