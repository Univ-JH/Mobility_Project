# MongoDB 연결 및 상태/이벤트 리포지토리 구현 계획서

## 1. 개요 및 목적
본 계획서는 **이동장치 안전 주행 시스템**의 핵심 데이터를 관리할 MongoDB 연결부(`core/database.py`) 및 데이터 액세스 계층(`repositories/`)의 구현 방향을 정의합니다. 
FastAPI 비동기 환경에 맞춰 설계되며, `.cursor/rules`에 명시된 **'안전 우선, 멱등성 보장, 계층 분리'** 원칙을 엄격하게 준수합니다.

---

## 2. 기술 스택 및 의존성
- **Driver**: `motor` (비동기 MongoDB 드라이버)
- **ODM/Validation**: `pydantic` (FastAPI의 기본 모델과 호환, 스키마 검증)
- **Environment**: FastAPI `Lifespan` 이벤트를 통한 DB 커넥션 관리

---

## 3. 디렉터리 구조 계획
백엔드 구조 설계 원칙에 따라 `repositories` 레이어를 분리하여, API 라우터나 서비스 로직에 DB 쿼리가 섞이지 않도록 합니다.

```text
backend/app/
  ├── core/
  │   └── database.py        # 1. MongoDB 클라이언트 및 생명주기 관리
  ├── schemas/
  │   └── events.py          # (API/DB 공통) 이벤트 Pydantic 모델
  └── repositories/
      ├── base.py            # 2. 공통 CRUD 추상화 BaseRepository
      ├── events_repo.py     # 3. 실시간 이벤트 저장소
      ├── devices_repo.py    # 4. 장치 상태/정책 저장소
      └── rides_repo.py      # 5. 주행 세션 저장소
```

---

## 4. 모듈별 세부 구현 계획

### 4.1. Core Database 연결 (`core/database.py`)
- **구현 내용**: `AsyncIOMotorClient` 객체를 전역(또는 의존성)으로 관리.
- **연결 생명주기**: FastAPI의 `@asynccontextmanager def lifespan(app: FastAPI)`을 활용하여, 서버 시작 시 연결하고 종료 시 안전하게 해제.
- **의존성 주입(DI)**: `def get_db()` 함수를 정의하여 FastAPI의 `Depends()`를 통해 각 Service/Repository에 데이터베이스 객체를 주입.

### 4.2. Base Repository (`repositories/base.py`)
- **구현 내용**: 제네릭(Generic)을 활용하여 모든 리포지토리가 공유할 수 있는 `create`, `find_by_id`, `update`, `delete` 공통 메서드 제공.
- **장점**: 코드 중복 제거 및 향후 테스트 시 Mocking 용이성 확보.

### 4.3. Event Repository (`repositories/events_repo.py`)
> **역할**: 장치 및 워커로부터 수신되는 대량의 텔레메트리/이벤트를 고속으로 안전하게 저장.

- **대상 컬렉션**: `events`
- **핵심 데이터 구조**:
  - `deviceId`, `rideId`, `eventType`, `severity`, `confidence`
  - `stateFrom`, `stateTo`, `eventAt`(장치 시각), `ingestedAt`(서버 수신 시각)
- **구현 정책**:
  - **멱등성(Idempotency) 보장**: `deviceId + rideId + seq` 조합에 대해 유니크 인덱스(`unique=True`)를 설정. 중복 이벤트 수신 시 덮어쓰거나(upsert) 충돌 에러를 무시(`InsertOne` 예외 처리)하여 중복 저장을 방지.
  - **인덱싱 전략**: 
    - `{ deviceId: 1, eventAt: -1 }`
    - `{ eventType: 1, eventAt: -1 }` (조회 속도 최적화)

### 4.4. Device Repository (`repositories/devices_repo.py`)
> **역할**: 장치의 현재 상태(State Machine)와 마지막 통신 시각 갱신.

- **대상 컬렉션**: `devices`
- **핵심 구현**: 
  - 상태 전이(State Transition) 업데이트 시 **Atomic 연산**(`$set`, `$currentDate`)을 사용하여 동시성 문제를 방지.
  - 상태 업데이트 함수: `update_device_state(device_id, new_state, last_seen)`

---

## 5. 예외 및 에러 처리 (Fail-Safe 정책)
- DB 연결 지연/장애 시, 무한 대기를 방지하기 위해 `serverSelectionTimeoutMS` (예: 5000ms) 설정.
- DB I/O 실패 시(비동기 워커 측), 메모리 버퍼링 및 백오프(Backoff) 재시도 로직과 연계할 수 있도록 예외(`PyMongoError`)를 명확한 커스텀 에러(`DatabaseConnectionError` 등)로 래핑하여 상위로 던짐.

---

## 6. 마일스톤 및 작업 순서 (진행 추천 단계)

*   **Step 1. 환경 설정**: `requirements.txt`에 `motor` 추가 및 `.env`에 `MONGODB_URL` 환경변수 세팅
*   **Step 2. Core DB 모듈 개발**: `database.py` 구현 및 FastAPI lifespan 연동 테스트
*   **Step 3. Base 및 Device/Event Repo 개발**: 리포지토리 클래스와 멱등성 검증 로직 작성
*   **Step 4. 앱 구동 시 인덱스 자동 생성 로직 추가**: 애플리케이션 시작 시 `create_index` 실행
*   **Step 5. 단위 테스트**: `pytest`와 `mongomock-motor` (혹은 실제 로컬 DB) 연동으로 CRUD 로직 검증

---
*위 계획서가 확인되면, 즉시 Step 1~2 (의존성 추가 및 Database Core 구현) 작업 코딩을 시작할 수 있습니다.*
