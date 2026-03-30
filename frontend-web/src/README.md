# frontend-web/src

웹 UI 소스 코드의 실제 구현을 담는 디렉터리다.

## 호환성
- 백엔드 API 계약(JSON shape, 에러코드, 응답 envelope)은 문서화된 `BACKEND_IMPLEMENTATION_PLAN.md`를 따른다.
- MQTT event 계약 필드는 `.cursor/rules/60-mqtt-event-contracts.mdc`를 따른다.

## 확장성
- 새로운 기능은 `api/`(통신)와 `screens/`(화면), `components/`(재사용 UI)로 분리한다.

## 가시성/명확성
- “실시간 스트림 파싱”과 “화면 상태”를 섞지 않는다(파싱은 `api/` 또는 전용 훅으로).

