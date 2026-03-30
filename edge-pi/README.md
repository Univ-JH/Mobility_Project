# edge-pi

Raspberry Pi 5 기반 엣지 영역이다. 하향 카메라로 인도/차도 추론을 수행하고, 센서/추론 결과와 헬멧 BLE 데이터를 융합해 제동(서보) 제어 명령을 만든다.

## 호환성
- MQTT payload 계약은 `.cursor/rules/60-mqtt-event-contracts.mdc`의 v1 스키마를 따른다.
- 제어 명령은 `ttlMs` 내 적용하고, 서버 ACK를 추적한다.

## 확장성
- AI 모델 교체(가벼운 분류기 -> 세그멘테이션 등)는 `src/ai/` 내부에서 캡슐화한다.
- 제동 정책/단계는 `src/control/`에서만 변경한다.

## 가시성/명확성
- 엣지는 로컬 로그를 남기되, 반드시 이벤트에는 `deviceId/rideId/seq`를 포함해 서버에서 추적 가능하게 한다.

