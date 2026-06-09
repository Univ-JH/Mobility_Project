"""
AI 비전 수신 모듈 테스트
- UDP 소켓 파서 로직 검증 (하드웨어 불필요)
- 실제 AI 프로세스 연동: 모의 UDP 패킷 전송 → 수신 확인
- fail-safe: unknown 수신 시 sidewalk + confidence=0 반환 검증

실행: python -m tests.test_vision_receiver  (edge-pi/ 루트에서)
"""
import sys
import os
import time
import socket
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.communication.comm_config import VISION_HOST, VISION_PORT

SEND_DELAY = 0.3


def test_parser_logic():
    """VisionReceiver._parse() 로직을 직접 호출하지 않고 동일 로직 재검증"""
    print("\n[1] UDP 패킷 파서 로직 검증 (하드웨어 불필요)")

    cases = [
        ("road,0.95",    "road",     0.95,  True),
        ("sidewalk,0.82","sidewalk", 0.82,  True),
        ("unknown,0.0",  "sidewalk", 0.0,   True),   # fail-safe
        ("1",            "road",     1.0,   True),   # 구버전
        ("0",            "sidewalk", 1.0,   True),   # 구버전
        ("garbage",      None,       None,  False),  # 무효
        ("road,abc",     "road",     1.0,   True),   # conf 파싱 실패 → 1.0
    ]

    from src.ai.vision_receiver import VisionReceiver
    vr = VisionReceiver.__new__(VisionReceiver)  # __init__ 없이 파서만 테스트

    all_pass = True
    for raw, exp_cls, exp_conf, should_pass in cases:
        surface, conf = vr._parse(raw)
        ok = (surface == exp_cls) and (conf == exp_conf if exp_conf is not None else True)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  {status}  '{raw}' → ({surface}, {conf})  기대: ({exp_cls}, {exp_conf})")

    print(f"  {'PASS' if all_pass else 'FAIL'} — 파서 전체")
    vr.sock.close()
    return all_pass


def test_udp_send_receive():
    """실제 UDP 소켓 수신 루프 테스트"""
    print(f"\n[2] UDP 수신 루프 테스트 ({VISION_HOST}:{VISION_PORT})")

    from src.ai.vision_receiver import VisionReceiver

    try:
        vr = VisionReceiver()
    except Exception as e:
        print(f"  FAIL — VisionReceiver 초기화 실패: {e}")
        return

    vr.start()
    time.sleep(0.3)

    # 모의 AI 프로세스: UDP 패킷 발송
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    test_packets = [
        ("road,0.91",     "road",     0.91),
        ("sidewalk,0.78", "sidewalk", 0.78),
        ("unknown,0.0",   "sidewalk", 0.0),
    ]

    all_pass = True
    for packet, exp_cls, exp_conf in test_packets:
        sender.sendto(packet.encode(), (VISION_HOST, VISION_PORT))
        time.sleep(SEND_DELAY)

        got_cls  = vr.get_surface_type()
        got_conf = vr.get_surface_confidence()
        ok = (got_cls == exp_cls) and (abs(got_conf - exp_conf) < 0.01)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  {status}  송신='{packet}'  수신=({got_cls}, {got_conf:.2f})  기대=({exp_cls}, {exp_conf})")

    sender.close()
    vr.stop()
    print(f"  {'PASS' if all_pass else 'FAIL'} — UDP 수신 루프")


def main():
    print("=" * 50)
    print("AI 비전 수신 모듈 테스트")
    print("=" * 50)
    test_parser_logic()
    test_udp_send_receive()


if __name__ == "__main__":
    main()
