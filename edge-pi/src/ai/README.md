# edge-pi/src/ai

AI 가속기 기반 인도/차도 추론(분류 또는 세그멘테이션 후 확률 요약)을 담당하는 영역이다.

## 호환성
- 출력은 MQTT telemetry의 `vision.surfaceClass`와 `vision.sidewalkProb`에 매핑된다.

## 확장성
- 모델 교체 시에도 출력 인터페이스(표면 클래스/확률)를 고정한다.
- 불확실성(unreliable/unknown)은 `surfaceClass=unknown` 또는 서버 정책에서 해석 가능한 방식으로 표현한다.

## 가시성/명확성
- 프레임 단건 추론 대신 시간 윈도우 안정화 결과를 로깅해 오판 여부를 추적한다.

