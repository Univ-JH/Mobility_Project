# backend/app/api

HTTP API 라우터와 요청/응답 DTO 조립을 담당하는 디렉터리다.

## 호환성
- 엔드포인트/응답 포맷: `BACKEND_IMPLEMENTATION_PLAN.md`의 `21) API 상세 명세`를 따른다.
- 에러 응답은 `22) API 에러코드 카탈로그`의 코드만 사용한다.

## 확장성
- 새로운 조회/관리 API는 `router` 단위로 추가하며, 비즈니스 로직은 `services/`로 이동한다.

## 가시성/명확성
- API 레이어에서는:
  - 입력 검증(스키마)만 수행
  - 구조화 로그의 필수 키를 유지(`traceId`, `correlationId`, `deviceId`, `rideId`)

