# backend/app/repositories

MongoDB 접근을 담당하는 디렉터리다.

## 호환성
- 컬렉션 스키마/인덱스는 `BACKEND_IMPLEMENTATION_PLAN.md`의 `24) MongoDB 문서 스키마 상세`를 기준으로 한다.
- 시간 기반 쿼리는 반드시 `deviceId + timestamp/eventAt` 인덱스 전략을 따른다.

## 확장성
- 원시 텔레메트리 저장량이 커지면 `telemetry_buckets` 중심으로 쿼리/저장 메서드를 확장한다.

## 가시성/명확성
- 저장/조회 시점의 중요한 필드는 항상 동일한 이름으로 유지한다.
  - 예: `eventAt`, `ingestedAt`, `ackAt`

