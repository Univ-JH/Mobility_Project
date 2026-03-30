# backend/app/services

정책 엔진, 상태 전이 승인, 응급 케이스 라이프사이클 등 “비즈니스 유스케이스”를 구현하는 디렉터리다.

## 호환성
- 서비스에서 발생하는 모든 안전 관련 결과는 Decision Object 형태로 표준화한다.
- 상태 전이는 `domain/`의 검증 결과를 기준으로만 승인한다.

## 확장성
- 새로운 정책 우선순위/충돌 해결 방식은 `services/policy_service` 같은 단위로 격리해 교체 가능하게 한다.
- 응급 흐름이 늘어나면 `EmergencyService` 확장 포인트를 유지한다.

## 가시성/명확성
- 서비스는 최소한 아래 필드가 포함된 구조화 로그를 남긴다:
  - `traceId`, `deviceId`, `rideId`, `eventType`(또는 전이 타입), `commandId`(해당 시)

