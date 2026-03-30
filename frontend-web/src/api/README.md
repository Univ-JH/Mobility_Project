# frontend-web/src/api

백엔드 API 통신 계층(HTTP)과, 필요 시 실시간 스트림(서버 제공 WS/스트림)을 다루는 영역이다.

## 호환성
- API 응답 envelope(`success/code/message/data/traceId`)를 강제한다.
- 이벤트 계약 필드는 `severity/confidence/reason/context` 기반으로 타입을 고정한다.

## 확장성
- 엔드포인트가 늘어나면 `clients/` 또는 `endpoints/`로 세분화 가능하나, 계약 파싱 위치는 유지한다.

## 가시성/명확성
- 통신 실패는 사용자 메시지로 맵핑하고, traceId를 로그/디버그에 노출한다.

