# frontend-mobile/src/api

백엔드 HTTP API 및 실시간 연결(WS/스트림 등)이 들어갈 통신 계층 디렉터리다.

## 호환성
- API 응답 envelope(`success/code/message/data/traceId`)를 강제한다.
- 응급 액션은 `caseId` 기반으로 전송한다.

## 확장성
- 실시간 연결 기술이 바뀌어도 API 인터페이스(함수/타입) 계층을 유지한다.

## 가시성/명확성
- 요청 실패는 traceId를 포함해 로그로 남기고 사용자 메시지를 분리한다.

