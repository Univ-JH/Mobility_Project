edge-pi/src/communication

헬멧 유닛(Arduino Nano 33 BLE)과의 블루투스 통신 및 백엔드 서버와의 MQTT 통신(telemetry/event/control/ack)을 담당하는 관문(Gateway) 영역이다.

## 1. 개요
* **특징**: 아두이노가 엣지단에서 센서(압력, 기울기, 가속도)의 원시 데이터를 1차 연산한 뒤, 통신 부하를 최소화한 상태값 문자열 형태로 전송.
* **핵심 규칙**: 데이터 지연 및 역전을 방지하는 **멱등성(Idempotency)** 보장, 연결 단절 시 즉각적인 경고를 발생시키는 **안전(Fail-Safe)** 로직 탑재.

## 2. 데이터 프로토콜 명세 (BLE Protocol: Arduino -> RPi)
`Q:[값],T:[값],W:[값],A:[값],S:[값]`

| 식별자 | 설명 (Description) | 값의 의미 (Values) |
| :--- | :--- | :--- |
| **Q** | 패킷 순번 (Sequence) | 단조 증가 정수 (중복 및 과거 데이터 무시용) |
| **T** | 타임스탬프 (Timestamp)| 데이터 생성 기준 시간 (Epoch ms/s) |
| **W** | 헬멧 착용 유무 (Worn) | 0: 미착용, 1: 착용 |
| **A** | 사고/전도 감지 (Accident)| 0: 정상, 1: 사고 발생 (기울기/충격 감지) |
| **S** | 주행 가속 상태 (Speed) | 0: 정상, 1: 급감속, 2: 급가속 |

## 3. 코드 구성 (Files)
* `comm_config.py`: 통신 관련 하드코딩 배제. BLE 기기 MAC 주소, 재연결 간격(Interval), 그리고 백엔드 서버 연동을 위한 MQTT v1 스키마 토픽(telemetry, event, control, ack) 상수 관리.
* `ble_manager.py`: `bleak` 기반 비동기 블루투스 통신 수행. 수신된 문자열을 파싱하고, `Q(seq)` 검증을 통해 유효한 최신 데이터만 딕셔너리 객체로 변환하여 상위 모듈 콜백으로 전달.
* `mqtt_client.py`: 정제된 이벤트 로그와 디바이스 상태를 서버 규격에 맞춰 퍼블리싱하고, 서버 제어 명령에 대한 ACK를 응답.

## 4. 제어 및 정책 연동 (Control & Policy 연동)
* `ble_manager.py`는 데이터 전달 역할뿐만 아니라, `W:0`(미착용) / `A:1`(사고)를 수신하거나 **BLE 연결이 예기치 않게 끊어졌을 경우** 자체적으로 `HIGH` 레벨의 구조화 로그(`JSON_LOG`)를 출력.
* 등록된 예외 콜백(Callback)을 통해 상위 `policy_engine.py`로 위험 상태를 즉각 전달하여, 시스템 우선순위에 따라 보수적 제동(RUNNING_LIMITED 또는 EMERGENCY_STOP)을 유도함.