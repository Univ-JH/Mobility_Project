# edge-pi/src/communication

서버와의 MQTT 통신(telemetry/event/control/ack)을 담당하는 영역이다.

## 1. 개요
* [cite_start]특징: 아두이노가 센서(FSR, 기울기, 가속도)의 원시 데이터를 1차 연산한 뒤, 단순화된 상태값(0 또는 1)만 전송

## 2. 데이터 프로토콜 명세 (Protocol)
`W:[값],A:[값],S:[값]`

| 식별자 | 설명 (Description) | 값의 의미 (Values) |
| :--- | :--- | :--- |
| **W** | 헬멧 착용 유무 (Worn) | 0: 미착용, 1: 착용 |
| **A** | 사고/전도 감지 (Accident) | 0: 정상, 1: 사고 발생 (기울기 감지) |
| **S** | 주행 속도/가속 상태 (Speed) | 0: 정상, 1: 급감속, 2: 급가속 |

## 3. 코드 구성
* `arduino_comm.py`: 하드웨어 설정값(`COMM_CONFIG`)을 포함하고 있으며, 수신된 텍스트를 시스템 연산용 객체(Dictionary)로 변환

## 4. 제어 연동 (Control 연동)
[cite_start]`control` 폴더의 로직은 이 모듈에서 반환된 `is_accident`가 `True`일 경우, 시스템 우선순위에 따라 즉시 EMERGENCY 제동을 호출