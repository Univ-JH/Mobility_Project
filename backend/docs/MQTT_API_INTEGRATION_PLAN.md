# 실시간 통신(MQTT) 및 API 연동 상세 계획서

## 1. 개요 및 목적
현재 백엔드의 MQTT 구독(수집) 및 API 엔드포인트는 단방향으로 DB에 데이터를 저장하거나 임시 모의(Mock) 동작을 수행하는 단계에 있습니다. 본 계획서는 **엣지 장치(Edge)와의 양방향 실시간 제어(Publish)**와 **정책 엔진(Policy Engine)을 통한 자동 안전 제동 프로세스**를 구현하기 위한 세부 계획을 담고 있습니다.

---

## 2. 핵심 구현 영역

### 2.1. 실제 제어 명령 발행 (MQTT Publish) 로직 완성
> **현재 상황**: `app/services/mqtt_service.py` 내의 `publish_control_command` 함수가 단순 `print`만 수행.
> **구현 계획**:
- `aiomqtt.Client`를 사용하여 실제 브로커로 메시지를 `publish`하도록 리팩터링합니다.
- `publish` 함수는 FastAPI의 Request-Response 흐름 내에서 병목을 유발하지 않도록 비동기 전송을 보장해야 합니다.
- 하드웨어 제어 명령(예: 브레이크, 모드 변경)이므로 **QoS 1 (At least once)** 레벨을 적용하여 명령 유실을 방어합니다.
- 제어 로그 컬렉션(`control_command_logs`)에 제어 발송 내역(상태: `PENDING`)을 기록합니다.

### 2.2. Ingestion Worker와 안전 정책 엔진(Policy Engine) 결합
> **현재 상황**: `app/workers/ingestion_worker.py`는 Payload를 검증하고 저장소에 `insert`만 수행.
> **구현 계획**:
- `app/services/policy_engine.py` (안전 정책 엔진) 모듈을 신설합니다.
- 워커가 텔레메트리/이벤트를 수신한 직후, 저장과 동시에 **정책 엔진을 호출**하여 다음을 평가합니다.
  - *시나리오 A*: 이벤트가 `sidewalk_detected` (인도 감지)이고 `confidence`가 높을 경우 ➡️ 정책 엔진이 `publish_control_command(action="set_limit_mode", params={"brakeLevel": 2})`를 자동 트리거합니다.
  - *시나리오 B*: 텔레메트리에서 `helmet.worn`이 `false`로 지속될 경우 ➡️ 장치를 `IDLE`로 강제 전환하고 구동을 잠급니다.

### 2.3. 응급 케이스 (Emergency Flow) 통합
API(사용자 개입)와 MQTT(장치 센서) 양방향에서 들어오는 응급 상황을 일관되게 처리합니다.
- **장치 발송 사고 (MQTT ➡️ API)**: 헬멧에서 충격(Fall) 이벤트 수신 ➡️ DB에 응급 이벤트 저장 ➡️ 프론트엔드 모바일 앱/웹으로 긴급 웹소켓(WebSocket) 푸시 전송.
- **앱 발송 구조 요청 (API ➡️ MQTT)**: 사용자가 앱의 SOS 버튼을 누름(`POST /v1/events/emergency`) ➡️ DB 기록 및 장치 본체에 '비상 알람(싸이렌/LED) 활성화' 제어 명령 발송.

---

## 3. 디렉터리 및 모듈 변경 계획

```text
backend/app/
  ├── services/
  │   ├── mqtt_service.py      # (수정) 실제 Publish 및 QoS 적용
  │   └── policy_engine.py     # (신규) 룰 기반 속도/상태 제어 결정 로직
  ├── workers/
  │   └── ingestion_worker.py  # (수정) 이벤트 파싱 직후 policy_engine 호출 연동
  └── api/v1/
      ├── devices.py           # (수정) 제어 API 호출 시 DB 제어 로그(ControlLog) 남기기
      └── stream.py            # (신규, 선택사항) 웹/앱에 실시간 알림을 주기 위한 WebSocket 라우터
```

---

## 4. 마일스톤 및 작업 순서 (진행 추천 단계)

*   **Step 1. MQTT Publish 구현**: `mqtt_service.py`에 `aiomqtt.Client`를 붙여 로컬 MQTT 브로커(`localhost:1883`)로 실제 제어 JSON 페이로드 발송 확인.
*   **Step 2. 정책 엔진(Policy Engine) 작성**: `policy_engine.py`를 구현하여 인도(Sidewalk) 감지 시 자동으로 속도 제한 제어가 내려가는 파이프라인 완성.
*   **Step 3. 응급(SOS) API 고도화**: `/v1/events/emergency` 호출 시 장치로 비상 알람 제어가 가도록 `mqtt_service` 연동.
*   **Step 4. 웹소켓(WebSocket) 추가 (향후)**: 대시보드에서 이벤트를 실시간으로 모니터링할 수 있도록 스트리밍 API 도입.

---
*위 계획서를 바탕으로, `Step 1 (실제 MQTT Publish 구현)`과 `Step 2 (정책 엔진 신설)` 코딩을 즉시 시작할 수 있습니다.*
