# 이동장치 안전 시스템 백엔드 구현 계획서 (구현 전)

## 1) 문서 목적과 범위

이 문서는 다음 시스템의 **백엔드 구현을 위한 상세 계획**을 정의한다.
- 헬멧(Arduino Nano 33 BLE)과 이동장치(Raspberry Pi 5)에서 발생하는 데이터 수집
- 위험 이벤트 판단 결과 저장 및 조회
- 정책(속도 제한/응급 로직) 관리
- 웹/웹앱 사용자와 장치 간 제어 인터페이스 제공

본 문서의 범위는 **서버 백엔드(FastAPI + MQTT + MongoDB + 운영 인프라)**이며, 펌웨어/프론트의 실제 코드 구현은 포함하지 않는다.

---

## 2) 백엔드 목표 (Why)

백엔드는 단순 API 서버가 아니라, 아래 4가지를 동시에 만족해야 한다.

1. **실시간성**: 위험 이벤트를 빠르게 수신/전달하고 상태를 즉시 반영
2. **안전성**: 불확실/장애 상황에서도 보수적 제어 정책을 유지
3. **추적성**: 사고 전후 맥락을 재현할 수 있는 로그/이벤트 저장
4. **운영성**: 장치 수 증가 시에도 확장 가능한 구조

---

## 3) 요구사항 재해석 (백엔드 관점)

원 요구사항 1~8을 백엔드로 전개하면 아래 기능이 필요하다.

- 헬멧 착용 여부, 기울기/가속도 이벤트를 수신하고 세션 상태 반영
- 라즈베리파이 추론 결과(인도/차도, 불확실성)를 수신하고 정책 계산
- 자동 제동/감속 명령 이력 저장 및 명령 전달 채널 제공
- BLE 단절/센서 이상/모델 불확실 등 장애 이벤트를 안전 등급으로 처리
- MQTT 기반 실시간 흐름 + HTTP 기반 설정/조회 흐름 동시 지원
- 사용자/장치/정책/주행 이력/응급 이벤트의 데이터 일관성 유지

---

## 4) 시스템 컨텍스트와 책임 경계

## 4.1 경계 정의
- **장치 측(Edge)**: 실시간 센싱/1차 판단/즉시 제어
- **백엔드 측(Server)**: 정책 배포, 이벤트 집계, 기록 보존, 사용자 인터페이스, 운영 모니터링

## 4.2 핵심 원칙
- 제동 여부의 최종 즉시 결정은 Edge가 담당하되, 백엔드는 정책과 기준값을 제공
- 서버 장애 시에도 Edge는 마지막 유효 정책으로 동작해야 함(오프라인 내성)
- 백엔드는 “나중 분석”뿐 아니라 “실시간 운영 가시성”을 동시에 제공

---

## 5) 제안 아키텍처

## 5.1 컴포넌트
- **API Gateway (FastAPI)**
  - 인증/인가, 장치 관리, 정책 CRUD, 이력 조회 API
- **MQTT Broker**
  - `telemetry/event/control` 실시간 채널
- **Ingestion Worker**
  - MQTT 수신 데이터 검증/정규화/저장
- **Policy Engine**
  - 장치별 정책 계산 및 변경 이력 관리
- **Alert Service**
  - 응급 이벤트 확정/중복 억제/알림 라우팅
- **MongoDB**
  - 운영 데이터 + 시계열 요약 + 이력 저장

## 5.2 배포 형태 (초기)
- **AWS + Docker 기반 배포**를 기본 전략으로 채택한다.
- 초기(단순 운영):
  - AWS `EC2` 1대에 Docker Compose로 `api`, `worker`, `mqtt`, `mongo` 컨테이너 분리
  - 운영 편의를 위해 도메인/인증서는 `Route 53 + ACM` 연동을 고려
- 중기(운영 안정화):
  - `api/worker`는 `ECS(Fargate)`로 분리 배포
  - DB는 관리형 서비스(`DocumentDB` 또는 `MongoDB Atlas on AWS`) 전환 검토
  - MQTT는 운영 복잡도/보안 요구에 따라 `EMQX managed` 또는 자가운영 브로커 이중화 검토
- 장기적으로:
  - 워커 수평 확장, 읽기 전용 API 분리, 로그/메트릭 스택 분리

## 5.3 AWS 책임 분리 원칙
- Edge 제어는 오프라인 내성을 위해 로컬 우선, AWS는 정책/기록/관측 책임을 맡는다.
- AWS 장애 시 Edge는 마지막 유효 정책으로 동작하고, 복구 후 이벤트를 재동기화한다.
- 네트워크 단절 구간의 데이터는 장치 버퍼링 후 순차 업로드한다.

---

## 6) 도메인 모델 설계

## 6.1 핵심 엔티티
- `User`: 관리자/운영자/일반 사용자 권한, 비상 연락처
- `Device`: 장치 식별자, 펌웨어 버전, 상태, 소유자
- `RideSession`: 주행 시작~종료 단위
- `Policy`: 속도 제한/응급 조건/신뢰도 임계치 등
- `Event`: 안전 관련 이벤트 로그
- `TelemetryBucket`: 초/분 단위 요약 데이터
- `ControlCommandLog`: 제어 명령 발행 및 결과
- `EmergencyCase`: 응급 의심~확정~해제 흐름

## 6.2 이벤트 유형(초안)
- `helmet_on`, `helmet_off`
- `harsh_acceleration`, `harsh_braking`
- `sidewalk_detected`, `road_detected`, `surface_unknown`
- `auto_brake_triggered`, `speed_limited`
- `fall_suspected`, `emergency_confirmed`, `emergency_cancelled`
- `ble_disconnected`, `sensor_fault`, `model_uncertain`

---

## 7) 상태 기계와 백엔드 반영 규칙

백엔드는 장치 상태를 저장할 때 단일 플래그가 아니라 상태 기계로 기록한다.

상태 예시:
- `IDLE`, `READY`, `RUNNING_NORMAL`, `RUNNING_LIMITED`, `AUTO_BRAKING`, `EMERGENCY`, `FAULT`

백엔드 규칙:
- 상태 전이는 `from`, `to`, `reason`, `source`, `confidence`, `timestamp`를 함께 저장
- 불법 전이(예: `IDLE -> AUTO_BRAKING`)는 오류 또는 `anomaly`로 기록
- `FAULT`/`EMERGENCY` 전이는 별도 우선순위 큐로 처리

---

## 8) API 설계 계획 (FastAPI)

## 8.1 인증/권한
- 사용자 인증: JWT 기반 액세스/리프레시
- 장치 인증: device token 또는 서명 기반 인증
- 역할 권한:
  - `admin`: 전체 정책/장치 관리
  - `operator`: 모니터링/응급 처리
  - `user`: 본인 장치/이력 조회

## 8.2 API 그룹
- `Auth API`: 로그인, 토큰 갱신, 로그아웃
- `Device API`: 장치 등록, 상태 조회, 할당/해제
- `Policy API`: 정책 생성/배포/롤백
- `Ride API`: 세션 목록/상세/요약
- `Event API`: 이벤트 검색, 필터, 페이징
- `Emergency API`: 응급 확인/취소/종결
- `Ops API`: 헬스체크, 버전, 내부 지표(관리자 전용)

## 8.3 응답 표준
- 공통 응답 포맷:
  - `success`, `code`, `message`, `data`, `traceId`
- 오류 코드 체계:
  - 인증/인가, 검증 실패, 상태 충돌, 리소스 없음, 내부 오류 분리

---

## 9) MQTT 계약(Contract) 계획

## 9.1 토픽 구조
- `device/{deviceId}/telemetry`
- `device/{deviceId}/event`
- `device/{deviceId}/status`
- `device/{deviceId}/control`
- `device/{deviceId}/ack`

## 9.2 필수 필드
- `deviceId`
- `timestamp` (단일 포맷으로 통일)
- `schemaVersion`
- `seq` (중복/누락 판별)

## 9.3 신뢰성 전략
- 중복 메시지는 `deviceId + seq + timestamp` 기준으로 멱등 처리
- 순서 역전이 발생해도 저장 후 재정렬 가능한 구조 유지
- QoS 레벨은 메시지 성격별 차등 적용(이벤트/제어 우선)

---

## 10) 데이터 모델 및 인덱스 계획 (MongoDB)

## 10.1 컬렉션
- `users`
- `devices`
- `device_policies`
- `ride_sessions`
- `events`
- `telemetry_buckets`
- `control_command_logs`
- `emergency_cases`
- `audit_logs`

## 10.2 인덱스(초기안)
- `events`: `{ deviceId: 1, timestamp: -1 }`, `{ eventType: 1, timestamp: -1 }`
- `ride_sessions`: `{ deviceId: 1, startTime: -1 }`, `{ userId: 1, startTime: -1 }`
- `telemetry_buckets`: `{ deviceId: 1, bucketTime: -1 }`
- `emergency_cases`: `{ status: 1, openedAt: -1 }`

## 10.3 보존 정책
- 원시 텔레메트리: 짧은 보존(예: 7~30일) + 집계 영구 보존
- 이벤트/응급/제어 로그: 규정에 맞춰 장기 보존
- TTL 인덱스 적용 대상과 미적용 대상을 구분

---

## 11) 안전 정책 엔진 설계 계획

## 11.1 정책 계층
- **글로벌 정책**: 전체 장치 공통 최소 안전 규칙
- **장치 정책**: 장치별 튜닝(브레이크 민감도, 속도 제한)
- **상황 정책**: 인도 감지/야간/BLE 불안정 등 조건부 정책

## 11.2 계산 순서(우선순위)
1. 법규/강제 안전 규칙
2. 응급/고위험 이벤트 기반 강제 제한
3. 장치/사용자 커스텀 정책
4. 기본 정책

## 11.3 변경 관리
- 정책 변경은 즉시 덮어쓰지 않고 버전 관리
- 롤백 가능해야 하며 변경 전/후 diff를 감사 로그에 저장

---

## 12) 장애/예외 시나리오 계획

핵심 원칙: “서비스 가용성보다 안전성 우선”

- MQTT 브로커 일시 장애:
  - 장치 측 버퍼링 + 서버 복구 후 재전송
- DB 지연/장애:
  - 실시간 응답 경로와 비동기 저장 경로 분리
- 중복 이벤트 폭주:
  - rate limit + dedup + 샘플링 조합
- 장치 시간 불일치:
  - 서버 수신 시각과 장치 시각 동시 저장
- 스키마 버전 불일치:
  - 하위 호환 파서 + 경고 이벤트 생성

---

## 13) 보안 계획

## 13.1 인증/인가
- 사용자: OAuth2/JWT
- 장치: 사전 등록 기반 토큰/서명
- 권한: 최소 권한 원칙(RBAC)

## 13.2 데이터 보호
- 전송 구간 TLS
- 민감정보 암호화 저장(필요 필드)
- 로그 마스킹(토큰, 연락처, 위치 세부좌표 정책적 축약)

## 13.3 감사(Audit)
- 정책 변경, 권한 변경, 응급 처리 이력은 `audit_logs`에 별도 저장

---

## 14) 관측성(Observability) 계획

## 14.1 로그
- JSON 구조화 로그
- 필수 키: `traceId`, `deviceId`, `eventType`, `severity`, `latencyMs`

## 14.2 메트릭
- MQTT 수신량/드롭률
- API P95/P99 지연시간
- 이벤트 처리 성공률
- 응급 이벤트 처리 소요시간
- 장치 온라인율

## 14.3 알림
- 임계 이벤트:
  - 브로커 다운
  - 이벤트 적체
  - 응급 이벤트 미처리 시간 초과

---

## 15) 테스트 전략 (백엔드 전용)

## 15.1 단위 테스트
- 정책 계산 로직
- 이벤트 정규화/검증 로직
- 상태 전이 검증

## 15.2 통합 테스트
- API + Mongo 연동
- MQTT 수신 -> 워커 처리 -> DB 저장 전체 흐름
- 응급 이벤트 확정/취소 플로우

## 15.3 계약 테스트
- MQTT payload schemaVersion별 호환성
- 프론트/앱 API 응답 계약 고정

## 15.4 부하/복원력 테스트
- 장치 동시 접속 증가(예: 100/500/1000대)
- 이벤트 burst 상황
- 브로커/DB 장애 주입 후 복구 시나리오

---

## 16) 개발/배포 환경 계획

## 16.1 환경 분리
- `local` / `staging` / `production`
- 환경별 DB, 브로커, 키 분리

## 16.2 CI/CD 초안
- PR 시: 정적검사 + 단위테스트 + 스키마 검증 + Docker 이미지 빌드 검증
- main 반영 시: 이미지 빌드 -> 이미지 레지스트리(ECR) 푸시 -> 스테이징 배포 -> 스모크 -> 프로덕션 승인

## 16.3 Docker 이미지/레지스트리 정책
- 서비스별 Dockerfile(`api`, `worker`)을 분리하고 태그 전략(`git-sha`, `semver`)을 병행한다.
- 베이스 이미지는 보안 업데이트가 용이한 경량 이미지를 사용한다.
- 이미지 취약점 스캔을 CI 단계에 포함한다.

## 16.4 AWS 인프라 운영 기준 (초안)
- 네트워크:
  - `VPC` 내부에 서비스 배치, 외부 공개는 API 엔드포인트만 허용
  - 보안 그룹으로 MQTT/DB 포트 접근 경로를 최소화
- 비밀정보:
  - 자격증명/토큰/DB 비밀번호는 `AWS Secrets Manager` 또는 `SSM Parameter Store`로 관리
- 관측성:
  - 로그는 `CloudWatch Logs`, 핵심 메트릭 알람은 `CloudWatch Alarms`로 운영
- 백업/복구:
  - DB 스냅샷/백업 주기와 복구 목표(RPO/RTO)를 사전 정의

## 16.5 마이그레이션
- MongoDB 스키마 변경은 마이그레이션 스크립트와 롤백 절차를 함께 관리

---

## 17) 구현 우선순위와 마일스톤

## M1. 기초 골격
- FastAPI 프로젝트 구조
- 인증/권한 최소 기능
- 장치 등록/조회 API

## M2. 실시간 파이프라인
- MQTT 브로커 연동
- Ingestion Worker
- 이벤트 저장/조회

## M3. 안전 정책 엔진
- 정책 CRUD + 버전/롤백
- 상태 기계 저장
- 제어 명령 로그

## M4. 응급 처리
- 응급 케이스 라이프사이클
- 중복 억제/우선순위 처리
- 운영 대시보드용 조회 API

## M5. 운영 고도화
- 메트릭/알림
- 부하 테스트
- 데이터 보존 최적화

---

## 18) 팀 역할 분담(권장)

- **Backend Lead**: 아키텍처/도메인/정책 엔진
- **API Engineer**: 인증/조회/관리 API
- **Data Engineer**: Mongo 모델/인덱스/보존 정책
- **Realtime Engineer**: MQTT/워커/멱등 처리
- **DevOps**: 배포/모니터링/보안 운영
- **QA**: 계약 테스트/부하/장애 복원력 검증

---

## 19) 오픈 이슈 (구현 전 확정 필요)

1. 응급 이벤트 확정 시간(`N초`)과 사용자 취소 UX 기준
2. 원시 텔레메트리 보존 기간 및 비용 한도
3. 장치 인증 방식(토큰 vs 서명)의 운영 난이도 비교
4. 정책 적용 우선순위 충돌 시 최종 결정 규칙
5. 제어 명령 ACK 타임아웃 기준과 재전송 횟수
6. AWS DB 선택(DocumentDB vs Atlas on AWS) 및 운영 비용 기준
7. MQTT 운영 방식(자가운영 vs managed)과 장애 책임 경계
8. 배포 타깃(초기 EC2 Compose vs 초기부터 ECS) 결정

---

## 20) 완료 기준 (Definition of Done for Backend Planning)

아래 항목이 모두 문서/리뷰로 확정되면 백엔드 구현 착수 가능:
- API 명세 초안 확정
- MQTT 계약 및 버전 정책 확정
- Mongo 컬렉션/인덱스/보존 정책 확정
- 상태 기계/정책 엔진 규칙 확정
- 보안/운영/알림 기준 확정
- 테스트 전략과 마일스톤 일정 확정

---

## 부록 A) 제안 디렉터리 구조 (구현 시 참고)

```text
backend/
  app/
    api/
    core/
    domain/
    services/
    repositories/
    schemas/
    workers/
  tests/
  scripts/
  docs/
```

본 구조는 구현 단계에서 세부 조정 가능하나, 계층 분리는 유지한다.

---

## 21) API 상세 명세 초안 (구현 전 확정본 v0.1)

## 21.1 인증/인가 API

### `POST /v1/auth/login`
- 목적: 사용자 로그인 및 토큰 발급
- Request:
  - `email`, `password`
- Response:
  - `accessToken`, `refreshToken`, `expiresIn`, `role`
- 실패:
  - `AUTH_INVALID_CREDENTIALS`, `AUTH_USER_DISABLED`

### `POST /v1/auth/refresh`
- 목적: 액세스 토큰 재발급
- Request:
  - `refreshToken`
- Response:
  - `accessToken`, `expiresIn`
- 실패:
  - `AUTH_REFRESH_EXPIRED`, `AUTH_REFRESH_REVOKED`

## 21.2 장치 관리 API

### `POST /v1/devices`
- 목적: 장치 등록(관리자)
- Request:
  - `deviceId`, `deviceType`, `fwVersion`, `ownerUserId`
- Response:
  - 생성된 장치 정보 + 초기 정책 버전

### `GET /v1/devices/{deviceId}/status`
- 목적: 최신 상태/마지막 이벤트 조회
- Response:
  - `state`, `lastSeenAt`, `helmetWorn`, `bleConnected`, `currentPolicyVersion`

### `POST /v1/devices/{deviceId}/assign`
- 목적: 사용자-장치 매핑 변경
- Request:
  - `ownerUserId`

## 21.3 정책 API

### `POST /v1/policies`
- 목적: 정책 생성
- Request 핵심:
  - `name`, `scope(global|device|condition)`, `rules`, `priority`
- Response:
  - `policyId`, `version`, `effectiveFrom`

### `POST /v1/policies/{policyId}/publish`
- 목적: 정책 배포
- 동작:
  - 현재 활성 정책과 충돌 검증 후 배포
  - 장치별 적용 결과를 비동기로 추적

### `POST /v1/policies/{policyId}/rollback`
- 목적: 이전 버전 복구
- Request:
  - `targetVersion`, `reason`

## 21.4 이벤트/세션 API

### `GET /v1/events`
- 필터:
  - `deviceId`, `eventType`, `severity`, `from`, `to`, `page`, `size`
- 응답:
  - 필터링된 이벤트 목록 + 페이지 정보

### `GET /v1/rides`
- 필터:
  - `deviceId`, `userId`, `from`, `to`
- 응답:
  - 세션 목록, 위험 이벤트 요약 통계

### `GET /v1/rides/{rideId}`
- 응답:
  - 상태 전이 타임라인 + 제동 명령 + 이벤트 분포

## 21.5 응급 API

### `POST /v1/emergencies/{caseId}/ack`
- 목적: 운영자 확인 접수
- Response:
  - `ackBy`, `ackAt`, `status`

### `POST /v1/emergencies/{caseId}/resolve`
- 목적: 응급 케이스 종결
- Request:
  - `resolutionType`, `note`

---

## 22) API 에러코드 카탈로그 (표준안)

- 인증/인가:
  - `AUTH_INVALID_CREDENTIALS`
  - `AUTH_TOKEN_EXPIRED`
  - `AUTH_FORBIDDEN`
- 요청 검증:
  - `REQ_VALIDATION_FAILED`
  - `REQ_UNSUPPORTED_SCHEMA_VERSION`
- 상태 충돌:
  - `STATE_TRANSITION_INVALID`
  - `POLICY_CONFLICT`
- 데이터/리소스:
  - `RESOURCE_NOT_FOUND`
  - `RESOURCE_DUPLICATED`
- 시스템:
  - `INTERNAL_ERROR`
  - `DEPENDENCY_UNAVAILABLE`

규칙:
- 모든 오류 응답에 `traceId` 포함
- 사용자 메시지(`message`)와 디버그용 코드(`code`) 분리

---

## 23) MQTT 페이로드 상세 계약 (v1)

## 23.1 Telemetry Payload (요약 전송)

```json
{
  "schemaVersion": 1,
  "deviceId": "dev-001",
  "timestamp": "2026-03-30T05:20:01.231Z",
  "seq": 12931,
  "rideId": "ride-20260330-0001",
  "helmet": {
    "worn": true,
    "pressureAvg": 0.72
  },
  "motion": {
    "accelX": 0.12,
    "accelY": -0.03,
    "tiltRoll": 3.2,
    "tiltPitch": -1.4
  },
  "vision": {
    "surfaceClass": "sidewalk",
    "sidewalkProb": 0.91
  },
  "health": {
    "bleConnected": true,
    "batteryPct": 78
  }
}
```

## 23.2 Event Payload (중요 이벤트)

```json
{
  "schemaVersion": 1,
  "deviceId": "dev-001",
  "timestamp": "2026-03-30T05:20:02.102Z",
  "seq": 12932,
  "rideId": "ride-20260330-0001",
  "eventType": "auto_brake_triggered",
  "severity": "high",
  "confidence": 0.93,
  "reason": "sidewalk_detected_and_speed_over_limit",
  "context": {
    "speedKph": 21.3,
    "sidewalkProb": 0.94,
    "helmetWorn": true
  }
}
```

## 23.3 Control Payload (서버->장치)

```json
{
  "schemaVersion": 1,
  "commandId": "cmd-84fd",
  "deviceId": "dev-001",
  "timestamp": "2026-03-30T05:20:02.120Z",
  "action": "set_limit_mode",
  "params": {
    "targetSpeedKph": 12,
    "brakeLevel": 2
  },
  "reason": "policy_limit_sidewalk",
  "ttlMs": 3000
}
```

---

## 24) MongoDB 문서 스키마 상세 (초안)

## 24.1 `devices`
- 필드:
  - `_id`, `deviceId`, `deviceType`, `ownerUserId`, `fwVersion`
  - `currentState`, `lastSeenAt`, `currentPolicyVersion`
  - `createdAt`, `updatedAt`

## 24.2 `ride_sessions`
- 필드:
  - `_id`, `rideId`, `deviceId`, `userId`
  - `startedAt`, `endedAt`, `durationSec`
  - `distanceM`, `avgSpeedKph`, `maxSpeedKph`
  - `riskSummary`(high/medium/low 건수)

## 24.3 `events`
- 필드:
  - `_id`, `deviceId`, `rideId`, `eventType`, `severity`, `confidence`
  - `stateFrom`, `stateTo`
  - `payload`, `ingestedAt`, `eventAt`
- 권장 인덱스:
  - `{ deviceId: 1, eventAt: -1 }`
  - `{ eventType: 1, eventAt: -1 }`
  - `{ severity: 1, eventAt: -1 }`

## 24.4 `control_command_logs`
- 필드:
  - `_id`, `commandId`, `deviceId`, `rideId`
  - `command`, `params`, `issuedAt`, `ackAt`, `result`
  - `timeoutMs`, `retryCount`

## 24.5 `emergency_cases`
- 필드:
  - `_id`, `caseId`, `deviceId`, `rideId`
  - `openedAt`, `status(open|acked|resolved|false_alarm)`
  - `ackBy`, `ackAt`, `resolvedAt`, `resolutionType`

---

## 25) 정책 엔진 규칙 표현 (DSL 초안)

정책은 JSON 기반 룰로 저장하고 버전 관리한다.

예시:
```json
{
  "policyId": "pol-sidewalk-v3",
  "version": 3,
  "priority": 80,
  "when": {
    "surfaceClass": "sidewalk",
    "speedKph": { "gt": 15 }
  },
  "then": {
    "mode": "RUNNING_LIMITED",
    "targetSpeedKph": 12,
    "brakeLevel": 1
  },
  "safetyLock": true
}
```

규칙:
- `priority` 높은 정책이 우선 적용
- 동순위 충돌 시 “더 안전한 결과”(더 낮은 속도, 더 높은 제동)를 선택
- 응급 규칙은 일반 규칙보다 항상 우선

---

## 26) 상태 전이 유효성 매트릭스

허용 전이 예시:
- `IDLE -> READY`
- `READY -> RUNNING_NORMAL`
- `RUNNING_NORMAL -> RUNNING_LIMITED`
- `RUNNING_LIMITED -> AUTO_BRAKING`
- `AUTO_BRAKING -> EMERGENCY`
- `ANY -> FAULT`
- `FAULT -> IDLE`

금지 전이 예시:
- `IDLE -> AUTO_BRAKING`
- `READY -> EMERGENCY` (충분한 이벤트 근거 없는 경우)

백엔드 검증:
- 전이 수신 시 유효성 검사
- 금지 전이는 저장하되 `anomaly=true`로 라벨링 및 경보

---

## 27) 성능/용량 계획 (초기 가정 기반)

초기 가정:
- 장치 100대, 장치당 telemetry 1Hz, event 평균 0.05Hz

예상 처리량:
- telemetry: 초당 100건
- events: 초당 5건

목표:
- ingestion 처리 성공률 99.9% 이상
- event 수신->저장 지연 P95 < 300ms
- control 발행->ACK 지연 P95 < 800ms

확장 계획:
- 장치 500대 이상 시 워커 다중 인스턴스 + 파티셔닝 고려

---

## 28) SLO/SLI/에러 버짓

SLI:
- API 성공률
- 이벤트 파이프라인 지연
- 응급 케이스 처리 시간

SLO(월간):
- API 가용성 99.5%
- 이벤트 저장 성공률 99.9%
- 응급 케이스 운영자 ACK P95 60초 이내

에러 버짓 정책:
- SLO 위반 추세 시 신규 기능보다 안정화 작업 우선

---

## 29) 테스트 케이스 상세 (구현 전 체크리스트)

필수 시나리오:
1. 헬멧 미착용 상태에서 `RUNNING` 전이 시도 -> 차단/경고 기록
2. BLE 단절 이벤트 -> `FAULT` 전이 + 제한 정책 적용
3. 인도 고확률 + 과속 -> 제한 명령 발행 + ACK 기록
4. 충격 + 기울기 지속 -> 응급 케이스 생성
5. 응급 케이스 ACK/RESOLVE 전 과정 감사 로그 확인
6. 중복 seq 이벤트 수신 -> 중복 저장 방지
7. 구버전 schema payload 수신 -> 하위 호환 처리

비기능:
- 부하 테스트(100/300/500 장치)
- 장애 주입(MQTT 일시 다운, Mongo 지연, 워커 재시작)

---

## 30) 보안 위협 모델 (요약)

주요 위협:
- 위조 장치가 가짜 이벤트 업로드
- 재전송 공격(replay)으로 제어 흐름 교란
- 권한 없는 사용자의 정책 변경

대응:
- 장치별 자격증명 + `seq/timestamp` 재전송 방지 검증
- 정책 API 관리자 권한 + 감사 로그 의무화
- 민감 경로(정책/응급)는 추가 인증 또는 짧은 토큰 수명 적용

---

## 31) 운영 런북(초안)

장애 대응 순서:
1. 장애 유형 분류(브로커/API/DB/워커)
2. 영향 범위 판단(장치 수, 응급 이벤트 누락 여부)
3. 임시 완화(읽기 전용 전환, 제어 보수 정책 강제)
4. 복구 후 데이터 정합성 점검
5. 사후 분석(RCA) 및 재발 방지 항목 등록

운영 지표 대시보드 최소 구성:
- 장치 온라인 수
- 최근 5분 이벤트 처리율
- 응급 오픈 케이스 수
- 제어 ACK 실패율

---

## 32) 백엔드 구현 착수 전 최종 승인 항목

- [ ] API 엔드포인트/에러코드 확정
- [ ] MQTT 토픽/페이로드 v1 확정
- [ ] Mongo 인덱스/TTL 정책 확정
- [ ] 상태 전이 유효성 매트릭스 승인
- [ ] 정책 우선순위/충돌 해결 규칙 승인
- [ ] SLO/운영 런북 승인
- [ ] AWS 인프라(네트워크/비밀관리/로그) 설계 승인
- [ ] Docker 이미지/배포 파이프라인(ECR 포함) 승인

위 항목 승인 완료 시, 구현 단계에서 변경 리스크를 크게 줄일 수 있다.

