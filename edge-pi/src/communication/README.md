# edge-pi/src/communication

서버와의 MQTT 통신(telemetry/event/control/ack)을 담당하는 영역이다.

## 호환성
- MQTT payload는 `.cursor/rules/60-mqtt-event-contracts.mdc`의 v1 계약을 따른다.

## 확장성
- 연결 재시도/오프라인 버퍼링 전략은 이 영역에서 캡슐화한다.

## 가시성/명확성
- 송수신 시 `deviceId`, `rideId`, `seq`, `commandId`를 함께 로그로 남긴다.

