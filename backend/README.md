# backend

FastAPI 기반 백엔드 서비스(HTTP API + MQTT ingestion + 정책/응급 처리 + MongoDB 저장) 코드와 문서를 담는 영역이다.

## 핵심 책임(Responsibility)
- HTTP 요청: 장치/정책/이력/응급 케이스 조회 및 운영 기능 제공
- MQTT 수신: 텔레메트리/이벤트/상태 입력의 정규화 + 멱등 저장
- 안전 제어 정책: 정책 DSL 평가 결과를 상태 전이와 함께 확정
- 제어 명령: 장치에 `control`을 발행하고 ACK를 추적

## 호환성(Compatibility)
- MQTT payload는 `.cursor/rules/60-mqtt-event-contracts.mdc`의 v1 계약을 기준으로 한다.
- `schemaVersion`이 다른 경우 서버는 하위 호환을 우선 지원하며, 불가 버전은 격리한다.
- API는 `BACKEND_IMPLEMENTATION_PLAN.md`의 `v0.1` API 엔벨로프/에러코드 규칙을 따른다.

## 확장성(Scalability)
- ingestion 워커를 수평 확장 가능하도록 “정규화 -> 저장” 경계를 명확히 둔다.
- 대량 이벤트는 원시 텔레메트리를 즉시 저장하지 않고 요약/버킷 저장 전략을 사용한다.

## 가시성/명확성(Observability)
- 구조화 로그 필수 키: `traceId`, `correlationId`, `deviceId`, `rideId`
- 제어/상태 전이/이벤트 저장에는 `eventType`, `severity`, `confidence`, `stateFrom`, `stateTo`, `commandId`를 포함한다.

## 포함할 하위 디렉터리
- `app/`: 실행 코드(계층 분리)
- `tests/`: 백엔드 테스트
- `docs/`: 백엔드 세부 문서(스키마/계약 보완)
- `scripts/`: 개발/운영 보조 스크립트(구현 전 문서만)

