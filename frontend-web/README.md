# frontend-web

React(웹) 기반 사용자/운영자 대시보드(상태 조회, 이벤트/주행 이력, 응급 케이스 처리, 정책 관리 UI)를 위한 영역이다.

## 호환성
- 백엔드 API는 `BACKEND_IMPLEMENTATION_PLAN.md`의 v0.1 API 상세 명세를 따른다.
- 실시간은 MQTT 브리지를 직접 다루지 않고(원칙), 서버에서 제공하는 HTTP 스트림/WS 또는 MQTT-브릿지 계층을 전제로 한다.
- 이벤트 표시 로직은 `.cursor/rules/60-mqtt-event-contracts.mdc`의 v1 `severity/confidence` 계약을 따른다.

## 확장성
- 이벤트 타입/정책 UI가 늘어나면:
  - `src/screens/`에 화면 추가
  - `src/components/`에 재사용 컴포넌트 추가
  - `src/api/`에 통신 로직만 확장

## 가시성/명확성
- “현재 장치 상태/최근 이벤트/응급 알림”은 반드시 동일한 기준(ritationId/rideId/seq)을 사용해 중복을 줄인다.

