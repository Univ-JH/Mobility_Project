# backend/app/workers

MQTT ingestion/정규화/저장, 비동기 처리(배치 저장/집계) 등을 수행하는 디렉터리다.

## 호환성
- MQTT 입력 계약은 `.cursor/rules/60-mqtt-event-contracts.mdc`의 v1 스키마를 따른다.
- ingestion 워커의 저장 규칙(멱등/중복/순서역전)은 `BACKEND_IMPLEMENTATION_PLAN.md`를 따른다.

## 확장성
- 이벤트 폭주 시 rate limit/샘플링/버킷 저장 전략을 워커 레벨에서 교체 가능해야 한다.

## 가시성/명확성
- ingestion 워커는 “저장된 것”과 “격리된 것(unsupported_schema/중복/검증 실패)”을 명확히 로그로 남긴다.

