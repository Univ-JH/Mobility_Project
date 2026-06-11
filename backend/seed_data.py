#!/usr/bin/env python3
"""Seed script — Busan Dong-eui University dummy data.

Usage:
    cd backend
    python seed_data.py
    python seed_data.py --drop   # drop collections first
"""
import sys
import random
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"
DB_NAME   = "mobility_db"

# Dong-eui University main campus: 35.1466 N, 129.0577 E
BASE_LAT = 35.1466
BASE_LNG = 129.0577

def ts(delta_minutes: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)

def loc(radius: float = 0.004) -> dict:
    return {
        "lat": BASE_LAT + random.uniform(-radius, radius),
        "lng": BASE_LNG + random.uniform(-radius, radius),
    }

def make_event(
    device_id, ride_id, seq, event_type, severity, confidence, reason,
    state_from=None, state_to=None, speed=10.0, sidewalk_prob=0.5,
    helmet_worn=True, delta_min=30, anomaly=False
) -> dict:
    return {
        "deviceId":  device_id,
        "rideId":    ride_id,
        "seq":       seq,
        "eventType": event_type,
        "severity":  severity,
        "confidence": confidence,
        "stateFrom": state_from,
        "stateTo":   state_to,
        "payload": {
            "schemaVersion": 1,
            "deviceId":  device_id,
            "timestamp": ts(delta_min).isoformat(),
            "seq":       seq,
            "rideId":    ride_id,
            "eventType": event_type,
            "severity":  severity,
            "confidence": confidence,
            "reason":    reason,
            "context": {
                "speedKph":     speed,
                "sidewalkProb": sidewalk_prob,
                "helmetWorn":   helmet_worn,
                "bleRssi":      random.randint(-85, -45),
            },
        },
        "eventAt":   ts(delta_min),
        "ingestedAt": ts(delta_min - 0.3),
        "anomaly":   anomaly,
    }


def seed(drop: bool = False):
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]

    if drop:
        for col in ["users", "devices", "events", "emergency_cases", "device_policies"]:
            db[col].drop()
            print(f"  dropped: {col}")

    # ── Users ──────────────────────────────────────────────────────────────────
    users = [
        {
            "userId": "user-busan-001",
            "email":  "kim.jisu@dongui.ac.kr",
            "name":   "김지수",
            "passwordHash": "$2b$12$placeholder_hash_001",
            "isAdmin": False,
            "safetyScore": 87.5,
            "appSettings": {},
            "createdAt": ts(4320),
            "updatedAt": ts(60),
        },
        {
            "userId": "user-busan-002",
            "email":  "lee.minjun@dongui.ac.kr",
            "name":   "이민준",
            "passwordHash": "$2b$12$placeholder_hash_002",
            "isAdmin": False,
            "safetyScore": 63.0,
            "appSettings": {},
            "createdAt": ts(2880),
            "updatedAt": ts(30),
        },
        {
            "userId": "user-busan-003",
            "email":  "park.sora@dongui.ac.kr",
            "name":   "박소라",
            "passwordHash": "$2b$12$placeholder_hash_003",
            "isAdmin": False,
            "safetyScore": 95.0,
            "appSettings": {},
            "createdAt": ts(1440),
            "updatedAt": ts(5),
        },
        {
            "userId": "user-busan-004",
            "email":  "choi.dawon@dongui.ac.kr",
            "name":   "최다원",
            "passwordHash": "$2b$12$placeholder_hash_004",
            "isAdmin": False,
            "safetyScore": 42.0,
            "appSettings": {},
            "createdAt": ts(720),
            "updatedAt": ts(200),
        },
    ]

    # ── Devices (6 devices, 다양한 상태) ──────────────────────────────────────
    devices = [
        # 정상 주행 중
        {
            "deviceId": "pi-busan-001",
            "deviceType": "scooter",
            "ownerUserId": "user-busan-001",
            "fwVersion": "1.2.0",
            "currentState": "RUNNING_NORMAL",
            "lastSeenAt":       ts(2),
            "lastHeartbeatAt":  ts(2),
            "helmetWorn":    True,
            "bleConnected":  True,
            "speedKph":      14.5,
            "currentRoadType": "road",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(4320),
            "updatedAt": ts(2),
        },
        # 인도 진입 → 속도 제한 중
        {
            "deviceId": "pi-busan-002",
            "deviceType": "scooter",
            "ownerUserId": "user-busan-002",
            "fwVersion": "1.2.0",
            "currentState": "RUNNING_LIMITED",
            "lastSeenAt":       ts(5),
            "lastHeartbeatAt":  ts(5),
            "helmetWorn":    False,
            "bleConnected":  True,
            "speedKph":      7.2,
            "currentRoadType": "sidewalk",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(2880),
            "updatedAt": ts(5),
        },
        # 비상 상태 (사고)
        {
            "deviceId": "pi-busan-003",
            "deviceType": "bike",
            "ownerUserId": "user-busan-003",
            "fwVersion": "1.1.5",
            "currentState": "EMERGENCY",
            "lastSeenAt":       ts(1),
            "lastHeartbeatAt":  ts(1),
            "helmetWorn":    True,
            "bleConnected":  False,
            "speedKph":      0.0,
            "currentRoadType": "unknown",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(1440),
            "updatedAt": ts(1),
        },
        # 대기 (주차 중)
        {
            "deviceId": "pi-busan-004",
            "deviceType": "scooter",
            "ownerUserId": "user-busan-001",
            "fwVersion": "1.2.0",
            "currentState": "IDLE",
            "lastSeenAt":       ts(120),
            "lastHeartbeatAt":  ts(120),
            "helmetWorn":    False,
            "bleConnected":  False,
            "speedKph":      0.0,
            "currentRoadType": "unknown",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(5760),
            "updatedAt": ts(120),
        },
        # 장치 오류
        {
            "deviceId": "pi-busan-005",
            "deviceType": "scooter",
            "ownerUserId": "user-busan-004",
            "fwVersion": "1.0.9",
            "currentState": "FAULT",
            "lastSeenAt":       ts(300),
            "lastHeartbeatAt":  ts(300),
            "helmetWorn":    False,
            "bleConnected":  False,
            "speedKph":      0.0,
            "currentRoadType": "unknown",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(8640),
            "updatedAt": ts(300),
        },
        # 출발 준비 완료
        {
            "deviceId": "pi-busan-006",
            "deviceType": "scooter",
            "ownerUserId": "user-busan-003",
            "fwVersion": "1.2.1",
            "currentState": "READY",
            "lastSeenAt":       ts(1),
            "lastHeartbeatAt":  ts(1),
            "helmetWorn":    True,
            "bleConnected":  True,
            "speedKph":      0.0,
            "currentRoadType": "unknown",
            "currentPolicyVersion": 1,
            "lastLocation":  loc(),
            "createdAt": ts(360),
            "updatedAt": ts(1),
        },
    ]

    # ── Events ────────────────────────────────────────────────────────────────
    R1 = "ride-busan-001-a"   # pi-busan-001 정상 주행 (인도→차도)
    R2 = "ride-busan-002-a"   # pi-busan-002 헬멧 미착용 + 급제동
    R3 = "ride-busan-003-a"   # pi-busan-003 충돌 비상
    R4 = "ride-busan-001-prev" # pi-busan-001 이전 라이드 (오경보)

    events = [
        # ── ride 1: 정상 주행 + 인도 감지 ──────────────────────────────────
        make_event("pi-busan-001", R1, 1,  "STATE_CHANGED",   "low",    1.00,
                   "승차 시작",            "IDLE",          "READY",
                   speed=0,  sidewalk_prob=0.0, delta_min=90),
        make_event("pi-busan-001", R1, 2,  "STATE_CHANGED",   "low",    1.00,
                   "헬멧 확인 후 출발",    "READY",         "RUNNING_NORMAL",
                   speed=5,  sidewalk_prob=0.1, delta_min=88),
        make_event("pi-busan-001", R1, 3,  "SIDEWALK_DETECTED","medium", 0.82,
                   "인도 진입 감지",
                   speed=13, sidewalk_prob=0.82, delta_min=80),
        make_event("pi-busan-001", R1, 4,  "STATE_CHANGED",   "medium", 0.82,
                   "인도 → 속도 제한 모드", "RUNNING_NORMAL","RUNNING_LIMITED",
                   speed=13, sidewalk_prob=0.82, delta_min=79),
        make_event("pi-busan-001", R1, 5,  "SPEED_LIMIT_APPLIED","medium",0.90,
                   "최고 8kph 적용",
                   speed=8,  sidewalk_prob=0.85, delta_min=75),
        make_event("pi-busan-001", R1, 6,  "SIDEWALK_CLEARED","low",    0.91,
                   "차도 복귀",
                   speed=8,  sidewalk_prob=0.15, delta_min=60),
        make_event("pi-busan-001", R1, 7,  "STATE_CHANGED",   "low",    0.91,
                   "정상 속도 재개",       "RUNNING_LIMITED","RUNNING_NORMAL",
                   speed=15, sidewalk_prob=0.15, delta_min=59),
        make_event("pi-busan-001", R1, 8,  "SIDEWALK_DETECTED","medium", 0.79,
                   "캠퍼스 내부 인도 재진입",
                   speed=11, sidewalk_prob=0.79, delta_min=40),
        make_event("pi-busan-001", R1, 9,  "STATE_CHANGED",   "medium", 0.79,
                   "속도 제한 재적용",     "RUNNING_NORMAL","RUNNING_LIMITED",
                   speed=11, sidewalk_prob=0.79, delta_min=39),
        make_event("pi-busan-001", R1, 10, "SIDEWALK_CLEARED","low",    0.88,
                   "차도 복귀 후 라이드 종료",
                   speed=5,  sidewalk_prob=0.12, delta_min=20),
        make_event("pi-busan-001", R1, 11, "STATE_CHANGED",   "low",    1.00,
                   "라이드 종료",          "RUNNING_LIMITED","IDLE",
                   speed=0,  sidewalk_prob=0.0,  delta_min=18),

        # ── ride 2: 헬멧 미착용 + 급제동 + AUTO_BRAKING ─────────────────────
        make_event("pi-busan-002", R2, 1,  "STATE_CHANGED",   "low",    1.00,
                   "승차 시작 (헬멧 없음)","IDLE",          "READY",
                   speed=0,  helmet_worn=False, delta_min=55),
        make_event("pi-busan-002", R2, 2,  "HELMET_OFF",      "high",   1.00,
                   "출발 시 헬멧 미감지",
                   speed=0,  helmet_worn=False, delta_min=54),
        make_event("pi-busan-002", R2, 3,  "STATE_CHANGED",   "medium", 1.00,
                   "헬멧 없음 → 제한 모드","READY",         "RUNNING_LIMITED",
                   speed=3,  sidewalk_prob=0.3, helmet_worn=False, delta_min=53),
        make_event("pi-busan-002", R2, 4,  "SIDEWALK_DETECTED","medium", 0.77,
                   "헬멧 없이 인도 진입",
                   speed=7,  sidewalk_prob=0.77, helmet_worn=False, delta_min=45),
        make_event("pi-busan-002", R2, 5,  "HARSH_BRAKE",     "high",   0.95,
                   "급격한 감속 감지 (충돌 위험)",
                   speed=18, sidewalk_prob=0.1,  helmet_worn=False, delta_min=35),
        make_event("pi-busan-002", R2, 6,  "STATE_CHANGED",   "high",   0.95,
                   "자동 제동 시작",       "RUNNING_LIMITED","AUTO_BRAKING",
                   speed=18, helmet_worn=False, delta_min=34),
        make_event("pi-busan-002", R2, 7,  "SPEED_LIMIT_APPLIED","high", 1.00,
                   "비상 속도 제한 0kph",
                   speed=0,  helmet_worn=False, delta_min=33),
        make_event("pi-busan-002", R2, 8,  "STATE_CHANGED",   "medium", 1.00,
                   "위험 해제 → 제한 모드 복귀","AUTO_BRAKING","RUNNING_LIMITED",
                   speed=3,  helmet_worn=False, delta_min=28),

        # ── ride 3: 충돌 → EMERGENCY ────────────────────────────────────────
        make_event("pi-busan-003", R3, 1,  "STATE_CHANGED",   "low",    1.00,
                   "승차 시작",            "IDLE",          "READY",
                   speed=0,  delta_min=22),
        make_event("pi-busan-003", R3, 2,  "STATE_CHANGED",   "low",    1.00,
                   "정상 주행",            "READY",         "RUNNING_NORMAL",
                   speed=12, delta_min=20),
        make_event("pi-busan-003", R3, 3,  "HARSH_BRAKE",     "high",   0.88,
                   "급격한 감속 (장애물)",
                   speed=20, sidewalk_prob=0.2, delta_min=14),
        make_event("pi-busan-003", R3, 4,  "CRASH_DETECTED",  "high",   0.97,
                   "고충격 가속도 스파이크 — 충돌 의심",
                   speed=21, sidewalk_prob=0.2, delta_min=12),
        make_event("pi-busan-003", R3, 5,  "STATE_CHANGED",   "high",   0.97,
                   "충돌 신호 → 자동 제동","RUNNING_NORMAL","AUTO_BRAKING",
                   speed=21, delta_min=12),
        make_event("pi-busan-003", R3, 6,  "STATE_CHANGED",   "high",   1.00,
                   "비상 선언",            "AUTO_BRAKING",  "EMERGENCY",
                   speed=0,  delta_min=11),
        make_event("pi-busan-003", R3, 7,  "EMERGENCY_SOS",   "high",   1.00,
                   "SOS 서버 전송",
                   speed=0,  delta_min=11),
        make_event("pi-busan-003", R3, 8,  "BLE_DISCONNECTED","medium", 1.00,
                   "충격 후 BLE 연결 끊김",
                   speed=0,  delta_min=10),

        # ── 이전 라이드 (pi-busan-001): 오경보 resolved ──────────────────────
        make_event("pi-busan-001", R4, 1,  "STATE_CHANGED",   "low",    1.00,
                   "승차 시작",            "IDLE",          "READY",
                   speed=0,  delta_min=1500),
        make_event("pi-busan-001", R4, 2,  "STATE_CHANGED",   "low",    1.00,
                   "정상 주행",            "READY",         "RUNNING_NORMAL",
                   speed=10, delta_min=1498),
        make_event("pi-busan-001", R4, 3,  "CRASH_DETECTED",  "high",   0.61,
                   "과속방지턱 충격 (낮은 신뢰도)",
                   speed=15, sidewalk_prob=0.1, delta_min=1490),
        make_event("pi-busan-001", R4, 4,  "STATE_CHANGED",   "high",   0.61,
                   "오경보 자동 제동",     "RUNNING_NORMAL","AUTO_BRAKING",
                   speed=15, delta_min=1490),
        make_event("pi-busan-001", R4, 5,  "STATE_CHANGED",   "medium", 1.00,
                   "오경보 해제 복귀",     "AUTO_BRAKING",  "RUNNING_NORMAL",
                   speed=10, delta_min=1488),
        make_event("pi-busan-001", R4, 6,  "STATE_CHANGED",   "low",    1.00,
                   "라이드 종료",          "RUNNING_NORMAL","IDLE",
                   speed=0,  delta_min=1450),

        # ── 이상 이벤트 (anomaly) ────────────────────────────────────────────
        make_event("pi-busan-002", R2, 99, "STATE_CHANGED",   "low",    0.50,
                   "잘못된 상태 전이 시도 (무시됨)","IDLE","EMERGENCY",
                   speed=0,  delta_min=15, anomaly=True),
    ]

    # ── Emergency Cases ───────────────────────────────────────────────────────
    emergency_cases = [
        {
            "caseId":    "case-busan-001",
            "deviceId":  "pi-busan-003",
            "rideId":    R3,
            "openedAt":  ts(11),
            "status":    "OPEN",
            "ackBy":     None,
            "ackAt":     None,
            "resolvedAt":     None,
            "resolutionType": None,
            "note": None,
        },
        {
            "caseId":    "case-busan-002",
            "deviceId":  "pi-busan-002",
            "rideId":    R2,
            "openedAt":  ts(600),
            "status":    "RESOLVED",
            "ackBy":     "admin@mobility.local",
            "ackAt":     ts(590),
            "resolvedAt": ts(550),
            "resolutionType": "manually_resolved",
            "note": "헬멧 미착용 + 급제동. 운전자 현장 확인 완료.",
        },
        {
            "caseId":    "case-busan-003",
            "deviceId":  "pi-busan-001",
            "rideId":    R4,
            "openedAt":  ts(1490),
            "status":    "FALSE_ALARM",
            "ackBy":     "admin@mobility.local",
            "ackAt":     ts(1480),
            "resolvedAt": ts(1460),
            "resolutionType": "false_alarm",
            "note": "과속방지턱 충격 오감지 (신뢰도 0.61). 드라이버 정상 확인.",
        },
        {
            "caseId":    "case-busan-004",
            "deviceId":  "pi-busan-005",
            "rideId":    "ride-busan-005-prev",
            "openedAt":  ts(350),
            "status":    "ACKED",
            "ackBy":     "admin@mobility.local",
            "ackAt":     ts(340),
            "resolvedAt": None,
            "resolutionType": None,
            "note": "장치 오류 확인 중.",
        },
    ]

    # ── Policies ──────────────────────────────────────────────────────────────
    policies = [
        {
            "policyId":  "policy-global-default",
            "version":   1,
            "name":      "기본 글로벌 정책",
            "scope":     "global",
            "priority":  100,
            "helmetRequired":    True,
            "maxSpeedKph":       25.0,
            "sidewalkBrakeLevel": 2,
            "isActive":  True,
            "effectiveFrom": ts(14400),
            "createdAt":     ts(14400),
        },
        {
            "policyId":  "policy-campus-dongui",
            "version":   1,
            "name":      "동의대 캠퍼스 구역 정책",
            "scope":     "zone",
            "priority":  200,
            "helmetRequired":    True,
            "maxSpeedKph":       10.0,
            "sidewalkBrakeLevel": 3,
            "isActive":  True,
            "effectiveFrom": ts(7200),
            "createdAt":     ts(7200),
        },
        {
            "policyId":  "policy-no-helmet-emergency",
            "version":   1,
            "name":      "헬멧 미착용 긴급 제한",
            "scope":     "global",
            "priority":  300,
            "helmetRequired":    True,
            "maxSpeedKph":       5.0,
            "sidewalkBrakeLevel": 5,
            "isActive":  False,
            "effectiveFrom": ts(3600),
            "createdAt":     ts(3600),
        },
    ]

    # ── Insert ────────────────────────────────────────────────────────────────
    collections = [
        ("users",            users,            "userId"),
        ("devices",          devices,          "deviceId"),
        ("events",           events,           "eventType"),
        ("emergency_cases",  emergency_cases,  "caseId"),
        ("device_policies",  policies,         "policyId"),
    ]

    total_ok = 0
    total_skip = 0
    for col_name, docs, key in collections:
        col = db[col_name]
        ok = skip = 0
        for doc in docs:
            try:
                col.insert_one(doc)
                ok += 1
            except Exception:
                skip += 1
        print(f"  {col_name:20s}  inserted={ok}  skipped(dup)={skip}")
        total_ok += ok
        total_skip += skip

    print(f"\nDone. total inserted={total_ok}, skipped={total_skip}")
    client.close()


if __name__ == "__main__":
    drop = "--drop" in sys.argv
    seed(drop=drop)
