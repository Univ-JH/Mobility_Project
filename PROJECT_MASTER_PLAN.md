# 이동장치 안전 주행 시스템 — 마스터 계획서 (v1.0)

> 작성일: 2026-04-01  
> 목적: 현재 프로젝트 구조 전체를 파악하고, 각 계층별 구현 범위·기술 결정·우선순위를 통합하여 팀이 공통 기준으로 개발할 수 있도록 정리한 단일 참조 문서.

---

## 목차

1. [프로젝트 전체 구조 현황 분석](#1-프로젝트-전체-구조-현황-분석)
2. [핵심 문제 정의 및 요구사항 재정리](#2-핵심-문제-정의-및-요구사항-재정리)
3. [전체 시스템 아키텍처](#3-전체-시스템-아키텍처)
4. [계층별 상세 설계](#4-계층별-상세-설계)
   - 4.1 헬멧 임베디드 (Arduino Nano 33 BLE)
   - 4.2 엣지 (Raspberry Pi 5)
   - 4.3 백엔드 서버 (FastAPI + MQTT + MongoDB)
   - 4.4 프론트엔드 웹 (React)
   - 4.5 프론트엔드 모바일 (React Native)
   - 4.6 인프라 (AWS + Docker)
5. [핵심 기술 판단 로직 상세](#5-핵심-기술-판단-로직-상세)
6. [안전 제어 상태 기계 (State Machine)](#6-안전-제어-상태-기계-state-machine)
7. [MQTT 통신 계약 (v1 확정)](#7-mqtt-통신-계약-v1-확정)
8. [데이터 모델 및 MongoDB 스키마](#8-데이터-모델-및-mongodb-스키마)
9. [API 설계 (FastAPI v0.1)](#9-api-설계-fastapi-v01)
10. [구현 로드맵 및 마일스톤](#10-구현-로드맵-및-마일스톤)
11. [위험요소(Risk) 및 대응 전략](#11-위험요소risk-및-대응-전략)
12. [미결 결정 사항 (Open Issues)](#12-미결-결정-사항-open-issues)

---

## 1. 프로젝트 전체 구조 현황 분석

### 1.1 현재 디렉터리 구조

```
Mobility_Project/
├── AGENTS.md                       # 개발 공통 규칙 (브랜치/커밋/안전 원칙)
├── README.md                       # 프로젝트 진입점 요약
├── SAFE_MOBILITY_SYSTEM_PLAN.md    # 전체 시스템 기획서 (H/W+S/W 통합)
├── BACKEND_IMPLEMENTATION_PLAN.md  # 백엔드 상세 구현 계획 (API/MQTT/DB)
├── PROJECT_MASTER_PLAN.md          # ← 이 문서 (종합 마스터 계획)
│
├── .cursor/rules/                  # 코드 규칙 (Cursor AI 연동)
│   ├── 00-core-standards.mdc       # 공통 핵심 규칙 (안전/관측성/보안)
│   ├── 05-repo-structure-and-naming.mdc
│   ├── 10-backend-fastapi-python.mdc
│   ├── 12-policy-engine-dsl.mdc
│   ├── 20-frontend-react-typescript.mdc
│   ├── 30-mobile-react-native.mdc
│   ├── 40-edge-raspberrypi.mdc
│   ├── 50-embedded-arduino-ble.mdc
│   └── 60-mqtt-event-contracts.mdc
│
├── backend/                        # FastAPI 서버
│   ├── app/
│   │   ├── api/                    # FastAPI 라우터 (엔드포인트 전용)
│   │   ├── domain/                 # 이벤트/상태/정책 타입 + 순수 로직
│   │   ├── services/               # 정책계산/상태전이/응급 라이프사이클
│   │   ├── repositories/           # MongoDB CRUD
│   │   ├── schemas/                # Pydantic DTO (API 계약)
│   │   └── workers/                # MQTT ingestion/정규화/배치저장
│   ├── tests/
│   └── docs/
│
├── edge-pi/                        # Raspberry Pi 5
│   └── src/
│       ├── ai/                     # 인도/차도 AI 추론 (모델 캡슐화)
│       ├── camera/                 # 카메라 파이프라인
│       ├── communication/          # MQTT/BLE 수신 처리
│       ├── control/                # 서보 브레이크 제어
│       └── state/                  # 엣지 상태 기계
│
├── embedded-helmet/                # Arduino Nano 33 BLE
│   └── src/
│       ├── sensors/                # 압력/IMU 센서 코드
│       └── ble/                    # BLE 패킷 전송
│
├── frontend-web/                   # React 웹 대시보드
│   └── src/
│       ├── api/                    # 백엔드 HTTP 통신
│       ├── components/             # 재사용 UI 컴포넌트
│       ├── hooks/                  # 커스텀 훅
│       ├── screens/                # 화면 단위 컴포넌트
│       └── state/                  # 전역/서버 상태 관리
│
├── frontend-mobile/                # React Native 모바일 앱
│   └── src/
│       ├── api/
│       ├── components/
│       ├── hooks/
│       ├── screens/
│       └── state/
│
├── infra/                          # 배포/운영 문서 (Docker, AWS)
└── docs/                           # 추가 명세 문서
    ├── specs/
    ├── data-dictionary/
    └── runbooks/
```

### 1.2 현재 상태 평가

| 영역 | 상태 | 비고 |
|------|------|------|
| 문서/기획 | ✅ 완성도 높음 | 3개 계획 문서 + 9개 코딩 규칙 파일 |
| 폴더 구조 | ✅ 골격 완성 | 실제 코드는 아직 없음 (README만) |
| 백엔드 코드 | ❌ 미구현 | 계획 문서만 존재 |
| 엣지 코드 | ❌ 미구현 | 폴더 구조만 존재 |
| 임베디드 코드 | ❌ 미구현 | 폴더 구조만 존재 |
| 프론트엔드 | ❌ 미구현 | 폴더 구조만 존재 |
| 인프라 | ❌ 미구현 | README만 존재 |

**결론:** 프로젝트는 "설계 완료, 구현 미착수" 상태이며, 현재 이 마스터 계획서 완성 후 구현 단계로 진입 가능하다.

---

## 2. 핵심 문제 정의 및 요구사항 재정리

### 2.1 해결하려는 실제 문제

2륜 개인형 이동장치(전동킥보드, 자전거 등)의 대표적 사고 원인:

1. **헬멧 미착용** — 착용 강제 수단 부재
2. **급가속/급정거** — 위험 행동 감지 피드백 없음
3. **인도 주행** — 보행자 사고 위험, 자동 감속 수단 없음
4. **사고 발생 시 늦은 대응** — 응급 감지 및 신고 시스템 부재
5. **H/W와 S/W 분리 운영** — 통합 모니터링/제어 불가

### 2.2 기능 요구사항 (8개 항목 재해석)

| # | 요구사항 | 담당 컴포넌트 | 핵심 기술 |
|---|----------|---------------|-----------|
| 1 | 헬멧 압력 센서로 착용 판단, 착용 시에만 주행 | Arduino + Pi | 다점 압력, 히스테리시스 |
| 2 | 헬멧 기울기 센서로 사고/응급 판단 | Arduino + Pi | IMU, 충격피크 조합 |
| 3 | 가속도 센서로 급가속/급정거 판단 | Arduino + Pi | 저역통과 필터, 임계치 |
| 4 | 하향 카메라 + AI 추론으로 인도/차도 분류 | Raspberry Pi | 경량 세그멘테이션/분류 모델 |
| 5 | 서보 모터로 브레이크 자동 조작 | Raspberry Pi | 단계형 제동, 캘리브레이션 |
| 6 | Arduino ↔ Raspberry Pi BLE 통신 | Arduino + Pi | BLE GATT, 재연결 정책 |
| 7 | Raspberry Pi에서 메타데이터 DB 저장 | Pi + 백엔드 | MQTT → FastAPI → MongoDB |
| 8 | 웹/웹앱으로 정보 확인 및 제어 | React + RN | API, 실시간 스트림 |

### 2.3 비기능 요구사항 및 KPI

| 항목 | 목표값 | 측정 방법 |
|------|--------|-----------|
| 헬멧 착용 판정 정확도 | ≥ 98% | 실사용 테스트 오탐/미탐 집계 |
| 인도/차도 분류 정확도 | ≥ 95% | 주야간 통합 테스트셋 |
| 위험 이벤트 감지 지연 | ≤ 300ms~1s | 이벤트 타임스탬프 차이 |
| 자동 제동 명령 반응 | ≤ 500ms | 제어 명령 발행~ACK |
| BLE 재연결 성공률 | ≥ 99% | 단절 횟수 대비 재연결 성공 |
| 이벤트 저장 지연 P95 | < 300ms | ingestion → persist |
| 제어 ACK 왕복 P95 | < 800ms | control 발행 → ack 수신 |

---

## 3. 전체 시스템 아키텍처

### 3.1 물리 계층 구성

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 영역                           │
│   [웹 브라우저 React]          [모바일 앱 React Native]      │
└────────────────┬────────────────────────┬───────────────────┘
                 │ HTTPS                  │ HTTPS
┌────────────────▼────────────────────────▼───────────────────┐
│                   AWS 클라우드 (서버 영역)                   │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │  FastAPI     │  │ MQTT Broker │  │    MongoDB       │   │
│  │  (HTTP API)  │  │ (Mosquitto/ │  │  (운영 데이터)   │   │
│  │              │  │  EMQX)      │  │                  │   │
│  └──────────────┘  └──────┬──────┘  └──────────────────┘   │
│                            │ MQTT (TLS)                      │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                이동장치 엣지 (Raspberry Pi 5)                │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │ 하향카메라│  │ AI 추론  │  │ 상태기계  │  │ 서보제어 │  │
│  │ 파이프라인│  │ (NPU/CPU)│  │ + 정책    │  │ (브레이크│  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────┘  │
│                    ▲ BLE (Bluetooth Low Energy)              │
└────────────────────┼────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              헬멧 임베디드 (Arduino Nano 33 BLE)             │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ 압력 센서    │  │ IMU/기울기  │  │  BLE 송신 모듈     │  │
│  │ (착용 판정)  │  │ (사고 판단) │  │  (텔레메트리/이벤트│  │
│  └──────────────┘  └─────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 논리 계층 (데이터 흐름)

```
센싱 Layer       →  판단 Layer        →  제어 Layer      →  기록/알림 Layer
─────────────────────────────────────────────────────────────────────────
압력/IMU/가속도      헬멧착용 여부          서보 브레이크       MongoDB 저장
하향 카메라 영상  →  인도/차도 분류     →  속도 제한 적용  →  MQTT publish
BLE 수신           위험도 계산            제동 명령 발행       응급 알림
                   상태 기계 전이         ACK 추적             웹/앱 UI 갱신
```

---

## 4. 계층별 상세 설계

### 4.1 헬멧 임베디드 (Arduino Nano 33 BLE)

#### 하드웨어 구성
- MCU: Arduino Nano 33 BLE
- 센서: 압력 센서 (2점 이상), LSM9DS1 IMU (가속도/자이로/기울기 내장)
- 통신: BLE (GATT 프로파일)

#### `src/sensors/` 구현 대상

**압력 센서 (착용 판정)**
```
착용 조건 (모두 충족):
  - 압력 합계 > T_on (예: 보정 후 0.6 normalized)
  - 좌우 편차(분산) < T_var (편중 착용 방지)
  - 유지 시간 > 2초 (순간 접촉 오탐 방지)

탈착 조건:
  - 압력 합계 < T_off (T_on보다 작은 히스테리시스 적용)
  - T_off = T_on * 0.7 (예시)

이벤트:
  - helmet_on: 착용 확정 → BLE 즉시 송신
  - helmet_off: 탈착 확정 → BLE 즉시 송신
```

**IMU 센서 (사고/응급 판단)**
```
사고 의심 조건 (모두 충족):
  - 가속도 피크 > A_impact (예: 3G 이상)
  - 기울기(롤/피치) > G_fall (예: 60도 이상)
  - 비정상 자세 유지 > D_persist (예: 3초)

응급 확정:
  - 사고 의심 이후 N초(기본 30초) 내 사용자 취소 없으면 응급 확정

이벤트:
  - fall_suspected: 사고 의심 → 즉시 송신
  - emergency_confirmed: N초 후 취소 없음 → 즉시 송신
  - emergency_cancelled: 사용자 취소 → 즉시 송신
```

**급가속/급정거 판단**
```
전처리:
  - 저역통과 필터 (노면 진동 제거, 차단 주파수 ~2Hz)
  - 중력 성분 제거 (자세각 보정)

급가속: forward_accel > +a_thr (예: 0.4G) for t > t_min (예: 0.3s)
급정거: forward_accel < -b_thr (예: -0.5G) for t > t_min (예: 0.2s)

이벤트:
  - harsh_acceleration
  - harsh_braking
```

#### `src/ble/` 구현 대상

```
BLE 패킷 구조:
  - Telemetry: 주기 송신 (1Hz, 주행 중 / 0.2Hz, 대기 중)
  - Event: 즉시 송신 (착용변화/충격/응급)

패킷 필수 포함:
  - seq (단조 증가, ride 단위)
  - timestamp (ms epoch)
  - rideId
  - battery

연결 상태 관리:
  DISCONNECTED → CONNECTING → CONNECTED → TRANSMITTING
  단절 감지 → 재연결 시도 (최대 N회, 지수 백오프)
  재연결 실패 시 → local buffer에 이벤트 적재
```

---

### 4.2 엣지 (Raspberry Pi 5)

#### `src/camera/` — 카메라 파이프라인

```
입력: 하향 카메라 (30fps 권장, 해상도 최소 480x360)
전처리:
  - 프레임 리사이즈 (추론 모델 입력 크기 맞춤)
  - 밝기/대비 정규화
  - 이상 프레임 필터 (너무 어둡거나 흔들림 심한 경우)

출력: 전처리된 프레임 -> AI 추론 모듈로 전달
```

#### `src/ai/` — 인도/차도 AI 추론

```
모델 선택:
  - 1순위: 경량 분류 모델 (MobileNet 계열, 인도/차도/불확실 3-class)
  - 2순위: 경량 세그멘테이션 (정확도 필요시 DeepLab-lite 등)
  - AI 가속기(Hailo-8 등) 활용 시 Hailo SDK로 최적화

추론 결과 안정화 (시간 윈도우 다수결):
  윈도우 크기: 최근 N프레임 (예: 10프레임 = 1/3초)
  결과 변경 조건: 신뢰도 0.7 이상 + 다수결 60% 이상

출력 상태:
  - sidewalk: 인도 확률 > 0.7
  - road: 차도 확률 > 0.7
  - unknown: 불확실 (보수적 정책 적용)
```

#### `src/state/` — 엣지 상태 기계

```
상태 목록:
  IDLE → READY → RUNNING_NORMAL → RUNNING_LIMITED → AUTO_BRAKING → EMERGENCY
  ANY → FAULT

전이 입력:
  - 헬멧 착용 이벤트 (BLE 수신)
  - 인도/차도 추론 결과
  - 급가속/급정거 감지
  - 서버 제어 명령 (MQTT control)
  - BLE/센서 장애 감지

Fail-Safe 원칙:
  - BLE 단절 → FAULT 전이 → 속도 제한
  - 추론 불확실 → unknown 정책 적용 (보수적)
  - 서버 미응답 → 마지막 유효 정책 유지
```

#### `src/control/` — 서보 브레이크 제어

```
제동 단계:
  LEVEL_0: 정상 (제동 없음)
  LEVEL_1: 경고 감속 (속도 제한 15kph)
  LEVEL_2: 강제 감속 (속도 제한 10kph, 서보 10% 인가)
  LEVEL_3: 비상 제동 (서보 최대 인가, 50% 이상)

캘리브레이션 테이블 (파일 관리):
  - servo_calibration.json에 각도↔제동력 매핑 저장
  - 코드에 하드코딩 금지

수동 브레이크 우선권:
  - 수동 브레이크 감지 시 서보 즉시 해제
  - 물리적 간섭 방지 설계 필수
```

#### `src/communication/` — MQTT 발행 + BLE 수신

```
BLE 수신:
  - Arduino Nano로부터 텔레메트리/이벤트 수신
  - 수신 데이터를 MQTT telemetry/event 페이로드로 변환

MQTT 발행:
  - device/{deviceId}/telemetry: 1Hz 주기
  - device/{deviceId}/event: 이벤트 발생 즉시
  - device/{deviceId}/ack: 제어 명령 ACK

MQTT 구독:
  - device/{deviceId}/control: 서버로부터 제어 명령 수신
```

---

### 4.3 백엔드 서버 (FastAPI + MQTT + MongoDB)

#### 전체 계층 구조

```
app/
├── api/           # FastAPI 라우터만 (요청/응답 조립)
├── domain/        # 이벤트 타입, 상태 정의, 정책 DSL 타입 (순수 Python)
├── services/      # 정책 평가, 상태 전이, 응급 라이프사이클
├── repositories/  # MongoDB CRUD (motor/beanie)
├── schemas/       # Pydantic v2 DTO (API 응답/요청 계약)
└── workers/       # MQTT ingestion 워커 (aiomqtt/paho)
```

#### 주요 서비스 상세

**Policy Engine (`services/policy_engine.py`)**
```python
# JSON DSL 기반 규칙 평가
# 입력: 현재 상태 컨텍스트 (surfaceClass, speedKph, helmetWorn, ...)
# 출력: Decision { mode, targetSpeedKph, brakeLevel, reason, confidence }

평가 순서:
  1. 응급 규칙 (emergency_* 이벤트 활성 시 최우선)
  2. 강제 안전 규칙 (법규/최소 안전)
  3. 상황 정책 (인도감지/야간/BLE불안정 조건부)
  4. 장치/사용자 정책
  5. 기본 정책

동순위 충돌 해결:
  - 더 낮은 targetSpeedKph 우선
  - 동률 시 더 높은 brakeLevel 우선
  - 동률 시 policyId 사전순
```

**State Machine (`services/state_machine.py`)**
```
허용 전이 매트릭스:
  IDLE         → READY (helmet_on + ble_connected)
  READY        → RUNNING_NORMAL (출발 조건 충족)
  RUNNING_NORMAL → RUNNING_LIMITED (sidewalk/반복 위험 감지)
  RUNNING_LIMITED → AUTO_BRAKING (고위험 이벤트)
  AUTO_BRAKING → EMERGENCY (충격 + 비정상 자세 지속)
  ANY          → FAULT (BLE단절/센서장애/서보불능)
  FAULT        → IDLE (복구 + 재인증)

전이 저장:
  { from, to, reason, source, confidence, timestamp }
  금지 전이 → anomaly=true 라벨 + 경보
```

**Emergency Service (`services/emergency_service.py`)**
```
응급 라이프사이클:
  open → acked → resolved / false_alarm

중복 억제:
  - 같은 rideId에서 30초 이내 동일 caseType → 하나로 병합

알림 라우팅:
  - 운영자 대시보드 알림
  - 모바일 앱 푸시
  - 비상 연락처 (설정된 경우)
```

**MQTT Ingestion Worker (`workers/ingestion_worker.py`)**
```
처리 흐름:
  수신 → 스키마 검증 → 정규화 → 멱등 체크 → 비동기 저장

멱등성:
  deviceId + rideId + seq 조합으로 중복 제거
  중복 수신은 dup 로그만 남기고 저장하지 않음

순서 역전:
  eventAt 기준 저장, 정렬은 조회 시 처리

실패 처리:
  저장 실패 → 재시도 (지수 백오프, 최대 3회)
  재시도 모두 실패 → dead letter queue (별도 로그)
```

---

### 4.4 프론트엔드 웹 (React)

#### 주요 화면 구성

| 화면 | 경로 | 기능 |
|------|------|------|
| 대시보드 | `/dashboard` | 장치 전체 상태 카드, 활성 응급 케이스 |
| 장치 상세 | `/devices/:id` | 실시간 상태, 현재 센서값, 최근 이벤트 |
| 주행 이력 | `/rides` | 세션 목록, 위험 이벤트 통계 |
| 이벤트 로그 | `/events` | 필터/페이징 이벤트 목록 |
| 정책 관리 | `/policies` | 정책 CRUD, 버전/롤백 |
| 응급 처리 | `/emergencies` | ACK/RESOLVE 플로우 |
| 설정 | `/settings` | 사용자 설정, 비상 연락처 |

#### 기술 스택 결정
- React 18 + TypeScript
- 상태 관리: React Query (서버 상태) + Zustand (UI 상태)
- 실시간: WebSocket 또는 Server-Sent Events (백엔드 브릿지 경유)
- UI 컴포넌트: 별도 디자인시스템 (shadcn/ui 또는 직접 구현)

---

### 4.5 프론트엔드 모바일 (React Native)

#### 주요 화면
- 홈: 내 장치 실시간 상태 (착용 여부, 주행 모드, 속도)
- 응급 알림: 응급 팝업 → 확인/취소 (N초 카운트다운)
- 주행 이력: 최근 세션 목록 및 이벤트 요약
- 설정: 비상 연락처, 알림 설정

#### 핵심 UX — 응급 확인/취소 플로우
```
1. fall_suspected 수신 → 전면 팝업 표시 + 진동 알림
2. 카운트다운 (30초) 표시
3. 사용자 "괜찮아요" 터치 → emergency_cancelled API 호출
4. 카운트다운 만료 → emergency_confirmed 자동 확정 → 운영자에게 알림
```

---

### 4.6 인프라 (AWS + Docker)

#### 초기 배포 구성 (MVP)
```yaml
# docker-compose.yml (EC2 1대)
services:
  api:       # FastAPI (uvicorn)
  worker:    # MQTT ingestion worker
  mqtt:      # Mosquitto or EMQX
  mongo:     # MongoDB (개발/스테이징)
```

#### 중기 배포 구성
```
AWS 구성:
  VPC → 서브넷 (public: ALB, private: ECS/DB)
  Route 53 + ACM: HTTPS 도메인
  ECS Fargate: api, worker 컨테이너
  DocumentDB 또는 MongoDB Atlas: DB
  EMQX Cloud 또는 자가운영: MQTT 브로커
  Secrets Manager: 인증키/DB비밀번호
  CloudWatch: 로그/메트릭/알람
  ECR: Docker 이미지 레지스트리
```

#### CI/CD 흐름
```
PR 생성
  → 정적검사 (ruff/mypy) + 단위테스트 + 스키마 검증 + Docker 빌드 검증

main 병합
  → Docker 이미지 빌드 → ECR push → staging 배포 → 스모크 테스트
  → 승인 → production 배포
```

---

## 5. 핵심 기술 판단 로직 상세

### 5.1 헬멧 착용 최종 판단 알고리즘

```
입력: pressure_left, pressure_right (0.0~1.0 normalized)
출력: helmet_state (WORN / NOT_WORN)

로직:
  pressure_sum = pressure_left + pressure_right
  pressure_var = |pressure_left - pressure_right|

  if pressure_sum > T_ON and pressure_var < T_VAR:
      worn_candidate = True
  else:
      worn_candidate = False

  # 히스테리시스 적용
  if current_state == NOT_WORN and worn_candidate:
      if wear_hold_timer >= WEAR_HOLD_SEC:  # 2초
          → 이벤트: helmet_on 발행
  if current_state == WORN and not worn_candidate:
      if not_wear_hold_timer >= NOT_WEAR_HOLD_SEC:  # 0.5초 빠른 탈착 감지
          → 이벤트: helmet_off 발행

안전 정책:
  - IDLE 상태에서 helmet_state == NOT_WORN → READY 전이 불가
  - RUNNING_* 상태에서 helmet_off → 단계 감속 → 정지
```

### 5.2 인도/차도 분류 → 제어 정책 매핑

```
추론 결과        확률 임계치    적용 정책
──────────────────────────────────────────────────
sidewalk         > 0.70       RUNNING_LIMITED (12kph)
road             > 0.70       RUNNING_NORMAL (제한 없음)
unknown          < 0.70       보수적 정책 (15kph 제한)
night/rain       (감지시)     unknown 처리와 동일

시간 윈도우:
  - 최근 10프레임 중 7프레임 이상 sidewalk → sidewalk 확정
  - 상태 변경 후 3초간 변경 억제 (과도한 전환 방지)
```

### 5.3 사고 의심 감지 스코어링

```
입력 신호별 가중치:
  충격 피크 (>3G): +50점
  급격한 기울기 변화 (>60도): +30점
  비정상 자세 유지 (>3초): +20점
  급정거 감지: +10점

스코어 임계치:
  > 60점: fall_suspected 이벤트 발행
  > 80점: 높은 확률 (confidence > 0.8 표기)

오탐 방지:
  정차(속도 ~0) 상태에서 기울기 변화 → 스코어 0.5 배정 (헬멧 벗어놓기 구분)
  출발 직전 진동 → t_min 조건으로 필터
```

---

## 6. 안전 제어 상태 기계 (State Machine)

### 6.1 상태 정의

| 상태 | 설명 | 제동 레벨 |
|------|------|-----------|
| `IDLE` | 대기 중, 헬멧 미착용 | 없음 (출발 불가) |
| `READY` | 헬멧 착용 확인, 출발 가능 | 없음 |
| `RUNNING_NORMAL` | 정상 주행 | 없음 |
| `RUNNING_LIMITED` | 속도 제한 주행 (인도 감지 등) | LEVEL_1 |
| `AUTO_BRAKING` | 자동 감속/제동 | LEVEL_2~3 |
| `EMERGENCY` | 사고/응급 처리 중 | LEVEL_3 |
| `FAULT` | 센서/통신 장애 | LEVEL_1 (보수 제한) |

### 6.2 전이 조건 상세

```
IDLE → READY
  조건: helmet_on 이벤트 + BLE 연결 정상
  실패 조건: helmet_off 상태 → 출발 차단 메시지 표시

READY → RUNNING_NORMAL
  조건: 출발(속도 > 0) + 모든 센서 정상

RUNNING_NORMAL → RUNNING_LIMITED
  조건: sidewalk_detected or (harsh_braking 3회 이상 / 5분)

RUNNING_* → AUTO_BRAKING
  조건: sidewalk + 과속 or fall_suspected or harsh_braking 단발 고위험

AUTO_BRAKING → EMERGENCY
  조건: fall_suspected + 비정상 자세 D초 이상 지속

ANY → FAULT
  조건: BLE 단절 > N초 or 센서 고장 감지 or 서보 응답 없음

FAULT → IDLE
  조건: 장애 복구 + 사용자 재확인 (앱에서 리셋 버튼)
```

### 6.3 상태 기계 저장 형식

```json
{
  "deviceId": "dev-001",
  "from": "RUNNING_NORMAL",
  "to": "RUNNING_LIMITED",
  "reason": "sidewalk_detected",
  "confidence": 0.87,
  "source": "edge_ai",
  "timestamp": "2026-04-01T12:00:00.000Z",
  "anomaly": false
}
```

---

## 7. MQTT 통신 계약 (v1 확정)

### 7.1 토픽 구조

| 방향 | 토픽 | QoS | 설명 |
|------|------|-----|------|
| Pi → 서버 | `device/{id}/telemetry` | 0 | 1Hz 주기 텔레메트리 |
| Pi → 서버 | `device/{id}/event` | 1 | 중요 이벤트 (즉시) |
| Pi → 서버 | `device/{id}/status` | 1 | 연결상태/헬스 |
| 서버 → Pi | `device/{id}/control` | 1 | 제어 명령 |
| Pi → 서버 | `device/{id}/ack` | 1 | 제어 명령 ACK |

### 7.2 Telemetry Payload (v1)

```json
{
  "schemaVersion": 1,
  "deviceId": "dev-001",
  "timestamp": "2026-04-01T12:00:01.000Z",
  "seq": 1024,
  "rideId": "ride-20260401-001",
  "helmet": {
    "worn": true,
    "pressureAvg": 0.75,
    "pressureLeft": 0.73,
    "pressureRight": 0.77
  },
  "motion": {
    "accelX": 0.12,
    "accelY": -0.03,
    "accelZ": 9.81,
    "tiltRoll": 3.2,
    "tiltPitch": -1.4,
    "harshEvent": null
  },
  "vision": {
    "surfaceClass": "sidewalk",
    "sidewalkProb": 0.89,
    "frameCount": 10,
    "windowConsensus": 0.80
  },
  "health": {
    "bleConnected": true,
    "batteryPct": 82,
    "bleRssi": -65,
    "cpuTempC": 52.3
  }
}
```

### 7.3 Event Payload (v1)

```json
{
  "schemaVersion": 1,
  "deviceId": "dev-001",
  "timestamp": "2026-04-01T12:00:02.000Z",
  "seq": 1025,
  "rideId": "ride-20260401-001",
  "eventType": "auto_brake_triggered",
  "severity": "high",
  "confidence": 0.91,
  "reason": "sidewalk_detected_speed_over_limit",
  "context": {
    "speedKph": 19.5,
    "sidewalkProb": 0.89,
    "helmetWorn": true,
    "bleRssi": -65
  }
}
```

### 7.4 이벤트 타입 목록 (v1 확정)

```
헬멧 관련:
  helmet_on, helmet_off

급가속/급정거:
  harsh_acceleration, harsh_braking

인도/차도:
  sidewalk_detected, road_detected, surface_unknown

자동 제어:
  auto_brake_triggered, speed_limited

사고/응급:
  fall_suspected, emergency_confirmed, emergency_cancelled

장애:
  ble_disconnected, sensor_fault, model_uncertain, servo_fault
```

---

## 8. 데이터 모델 및 MongoDB 스키마

### 8.1 컬렉션 목록

| 컬렉션 | 목적 | 보존 정책 |
|--------|------|-----------|
| `users` | 사용자 계정/권한/연락처 | 영구 |
| `devices` | 장치 등록 정보/현재 상태 | 영구 |
| `device_policies` | 정책 DSL 버전 이력 | 영구 |
| `ride_sessions` | 주행 세션 요약 | 1년+ |
| `events` | 안전 이벤트 로그 | 6개월+ |
| `telemetry_buckets` | 분 단위 요약 통계 | 30일 |
| `control_command_logs` | 제어 명령 + ACK 이력 | 6개월 |
| `emergency_cases` | 응급 케이스 라이프사이클 | 영구 |
| `audit_logs` | 정책/권한 변경 감사 | 영구 |

### 8.2 핵심 스키마

**events 컬렉션**
```json
{
  "_id": "ObjectId",
  "deviceId": "dev-001",
  "rideId": "ride-...",
  "eventType": "auto_brake_triggered",
  "severity": "high",
  "confidence": 0.91,
  "stateFrom": "RUNNING_NORMAL",
  "stateTo": "RUNNING_LIMITED",
  "payload": { ...원본 컨텍스트... },
  "eventAt": "ISODate (장치 시각)",
  "ingestedAt": "ISODate (서버 수신)",
  "anomaly": false
}
```

**인덱스**
```javascript
// events
{ deviceId: 1, eventAt: -1 }        // 장치별 최신 이벤트 조회
{ eventType: 1, eventAt: -1 }        // 타입별 집계
{ severity: 1, eventAt: -1 }         // 고위험 이벤트 필터
{ rideId: 1, eventAt: 1 }            // 세션별 전체 이벤트

// ride_sessions
{ deviceId: 1, startedAt: -1 }
{ userId: 1, startedAt: -1 }

// telemetry_buckets
{ deviceId: 1, bucketTime: -1 }      // TTL 30일 적용

// emergency_cases
{ status: 1, openedAt: -1 }
```

---

## 9. API 설계 (FastAPI v0.1)

### 9.1 공통 응답 포맷

```json
{
  "success": true,
  "code": "OK",
  "message": "성공",
  "data": { ... },
  "traceId": "trace-abc123"
}
```

### 9.2 Endpoint 목록

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| POST | `/v1/auth/login` | - | 로그인, 토큰 발급 |
| POST | `/v1/auth/refresh` | - | 토큰 갱신 |
| POST | `/v1/devices` | admin | 장치 등록 |
| GET | `/v1/devices/{id}/status` | operator+ | 장치 최신 상태 |
| POST | `/v1/devices/{id}/assign` | admin | 장치-사용자 매핑 |
| POST | `/v1/policies` | admin | 정책 생성 |
| POST | `/v1/policies/{id}/publish` | admin | 정책 배포 |
| POST | `/v1/policies/{id}/rollback` | admin | 정책 롤백 |
| GET | `/v1/events` | operator+ | 이벤트 목록 (필터/페이징) |
| GET | `/v1/rides` | user+ | 주행 세션 목록 |
| GET | `/v1/rides/{rideId}` | user+ | 세션 상세 + 타임라인 |
| POST | `/v1/emergencies/{caseId}/ack` | operator+ | 응급 확인 |
| POST | `/v1/emergencies/{caseId}/resolve` | operator+ | 응급 종결 |
| GET | `/v1/ops/health` | admin | 헬스 체크 |

---

## 10. 구현 로드맵 및 마일스톤

### Phase 0 — 환경 설정 (1주)
- [ ] 개발 환경 통일 (Python 버전, Node 버전, Arduino IDE)
- [ ] Git 브랜치 전략 확정 (`feature/fix/docs/chore`)
- [ ] Docker Compose 로컬 개발 환경 구성 (MongoDB + MQTT 브로커)
- [ ] `.env.example` 및 환경 변수 목록 확정
- [ ] 미결 결정 사항 (Section 12) 팀 결정

### Phase 1 — 헬멧 노드 프로토타입 (2~3주)
- [ ] 압력 센서 2점 회로 구성 및 Arduino 코드 작성
- [ ] 착용/탈착 판정 로직 + 히스테리시스 구현
- [ ] LSM9DS1 IMU 데이터 수집 + 저역통과 필터
- [ ] 사고 의심 스코어링 로직 구현
- [ ] BLE GATT 프로파일 설계 + 텔레메트리 주기 송신
- [ ] BLE 재연결 정책 구현
- **검증:** 착용/미착용 100회 테스트 (목표: 98% 정확도)

### Phase 2 — 이동장치 엣지 프로토타입 (3~4주)
- [ ] 하향 카메라 파이프라인 구성 (Pi Camera 또는 USB)
- [ ] 인도/차도 분류 모델 학습 또는 사전학습 모델 파인튜닝
- [ ] AI 가속기 연동 (Hailo 또는 CPU 추론으로 시작)
- [ ] 시간 윈도우 다수결 안정화 로직
- [ ] 서보 브레이크 캘리브레이션 + 단계 제동 구현
- [ ] BLE Central 역할 구현 (Arduino 수신)
- [ ] 엣지 상태 기계 구현
- **검증:** 인도/차도 분류 정확도 (목표: 95%)

### Phase 3 — 백엔드 기초 + 통신 파이프라인 (3~4주)
- [ ] FastAPI 프로젝트 구조 + 인증/인가 구현
- [ ] MongoDB 컬렉션/인덱스 생성 스크립트
- [ ] MQTT ingestion 워커 구현
- [ ] 이벤트 정규화/멱등 처리 구현
- [ ] 정책 엔진 DSL 구현 + 단위 테스트
- [ ] 상태 전이 검증 + 저장 구현
- [ ] Pi → MQTT → 서버 → DB 전체 파이프라인 통합
- **검증:** 단위 테스트 커버리지 + 통합 파이프라인 스모크 테스트

### Phase 4 — 응급 처리 + 제어 명령 (2주)
- [ ] 응급 케이스 라이프사이클 구현
- [ ] 서버→Pi 제어 명령 + ACK 추적
- [ ] 알림 라우팅 구현 (운영자/앱)
- [ ] 헬멧-Pi-서버 종단간 응급 시나리오 검증

### Phase 5 — 프론트엔드 구현 (3~4주)
- [ ] React 웹 대시보드 구현 (주요 화면 5개)
- [ ] React Native 앱 구현 (응급 알림 + 상태 화면)
- [ ] 실시간 데이터 연동 (WebSocket/SSE)
- [ ] 응급 확인/취소 UX 구현

### Phase 6 — 현장 통합 테스트 + 튜닝 (3~4주)
- [ ] 전체 시스템 종단간 통합 시나리오 테스트
- [ ] 다양한 노면/시간대/날씨 조건 현장 테스트
- [ ] 임계치/모델 튜닝 (오탐/미탐 분석)
- [ ] 부하 테스트 + 장애 주입 테스트
- [ ] AWS 스테이징 배포 + 운영 지표 확인

---

## 11. 위험요소(Risk) 및 대응 전략

### 기술적 위험

| 위험 | 가능성 | 영향 | 대응 |
|------|--------|------|------|
| 인도/차도 AI 모델 야간/우천 성능 저하 | 높음 | 높음 | 불확실 시 unknown 처리, 지속 데이터 수집 후 재학습 |
| BLE 주행 중 불안정 | 중간 | 높음 | 재연결 정책, FAULT 상태 + 보수 모드 |
| 압력 센서 오탐 (순간 접촉) | 중간 | 높음 | 히스테리시스 + 유지시간 조건 |
| 서보 기계적 마모/오정렬 | 중간 | 높음 | 캘리브레이션 주기적 실행, 수동 우선권 |
| Pi 열/전력 문제 | 중간 | 중간 | 온도 모니터링, 저전력 모드 설계 |
| MQTT 브로커 장애 | 낮음 | 높음 | 엣지 버퍼링, 복구 후 재전송 |

### 프로젝트 위험

| 위험 | 대응 |
|------|------|
| AI 모델 학습 데이터 수집 시간 부족 | 공개 데이터셋 + 소량 현장 데이터 fine-tuning |
| H/W 조달 지연 | 소프트웨어 시뮬레이터로 병행 개발 |
| AWS 비용 초과 | 스테이징에만 클라우드, 로컬 우선 개발 |
| 팀원 역할 불균형 | Phase별 담당 명확화 (12절 참조) |

---

## 12. 미결 결정 사항 (Open Issues)

구현 착수 전 팀 합의가 필요한 항목:

| # | 항목 | 선택지 | 권장 |
|---|------|--------|------|
| 1 | 응급 확정 대기 시간(N초) | 15초 / 30초 / 60초 | 30초 권장 |
| 2 | 인도/차도 모델 초기 전략 | 분류(빠름/단순) vs 세그멘테이션(정밀) | 분류로 시작, 추후 전환 |
| 3 | AI 가속기 사용 여부 | Hailo-8 vs CPU 추론 | CPU로 시작 (가속기 추가) |
| 4 | MQTT 브로커 선택 | 자가운영 Mosquitto vs EMQX Cloud | Mosquitto로 시작 |
| 5 | MongoDB 배포 | Atlas Free/M10 vs EC2 자가운영 | Atlas M10 권장 |
| 6 | 원시 텔레메트리 보존 기간 | 7일 / 30일 | 7일 원시 + 영구 집계 |
| 7 | 장치 인증 방식 | Pre-shared token vs JWT 서명 | Pre-shared token (초기) |
| 8 | 압력 센서 점수 (1점 vs 2점) | 단일 vs 2점 | 2점 권장 (정확도) |
| 9 | 비상 연락처 알림 방식 | SMS vs 앱 푸시만 | 앱 푸시 우선, SMS 추후 |
| 10 | 웹 실시간 방식 | WebSocket vs SSE | SSE (단순, 이벤트 단방향) |

---

## 부록 A: 담당 역할 권장 분배

| 역할 | 담당 영역 |
|------|-----------|
| 임베디드 | Arduino 센서/BLE 코드 (`embedded-helmet/`) |
| 엣지/AI | Raspberry Pi 카메라/추론/제동 제어 (`edge-pi/`) |
| 백엔드 | FastAPI + MQTT + MongoDB + 정책 엔진 (`backend/`) |
| 프론트엔드 | React 웹 + React Native 앱 (`frontend-*/`) |
| 인프라/DevOps | Docker + AWS + CI/CD (`infra/`) |

## 부록 B: 테스트 시나리오 체크리스트

### 안전 Critical 시나리오 (Phase 3 완료 전 반드시 검증)
- [ ] 헬멧 미착용 상태에서 출발 시도 → 차단
- [ ] 주행 중 헬멧 탈착 → 단계 감속 → 정지
- [ ] BLE 단절 → FAULT 전이 → 속도 제한
- [ ] 인도 감지 + 과속 → AUTO_BRAKING 전이
- [ ] 충격 + 비정상 자세 지속 → 응급 케이스 생성
- [ ] 응급 ACK/RESOLVE 전 과정 감사 로그 확인
- [ ] 중복 seq 이벤트 수신 → 중복 저장 방지 확인
- [ ] 구 버전 schema payload → 하위 호환 처리

### 비기능 테스트
- [ ] 이벤트 저장 지연 P95 < 300ms 달성 확인
- [ ] 제어 ACK 왕복 P95 < 800ms 달성 확인
- [ ] 장치 100대 동시 telemetry 부하 테스트
- [ ] MQTT 브로커 순간 다운 후 복구 + 버퍼 재전송 확인
