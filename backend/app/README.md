# backend/app

백엔드 애플리케이션 실행 코드를 계층으로 분리한 디렉터리다.

## 호환성
- API DTO(Pydantic)와 MQTT payload 계약은 v1 스키마를 기준으로 1:1 매핑한다.
- 상태 전이/이벤트 타입 문자열은 문서 계약에 고정한다.

## 확장성
- 새로운 이벤트 타입/정책 DSL을 추가할 때 `domain/`과 `services/` 중심으로 확장한다.
- DB 쿼리 변경은 `repositories/`에서만 수행한다.

## 가시성/명확성
- `api/`: 라우터(엔드포인트)만 둔다.
- `services/`: 도메인 규칙/정책 엔진/응급 라이프사이클을 둔다.
- `repositories/`: MongoDB 접근만 둔다.
- `workers/`: MQTT ingestion/정규화/배치 저장을 둔다.

## 포함 디렉터리
- `api/`, `domain/`, `services/`, `repositories/`, `schemas/`, `workers/`

