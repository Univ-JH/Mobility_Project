# Backend

이동장치 안전 주행 시스템의 주행 데이터를 수집하고, 중앙 안전 정책에 맞춰 기기들을 통제하며, 대시보드 및 모바일 앱에 유의미한 정보를 서빙하는 메인 서버 환경입니다.

## 기술 스택
- **Framework & Language**: FastAPI / Python 3.10+
- **Database**: MongoDB (비동기 처리: `motor` / `beanie`)
- **API 인터페이스**: HTTP REST API / WebSocket (실시간 관제)
- **메시징 프로토콜**: MQTT (Edge ↔ 서버 / 송수신 워커용 `aiomqtt`)

## 폴더 설계
- `app/api/`: REST 엔드포인트(FastAPI 라우터). 오직 인입/반환 껍데기 역할만 수행.
- `app/domain/`: 도메인 이벤트 타입, 인터페이스, 상태 정의 및 정책 DSL 모음.
- `app/services/`: 핵심 비즈니스 로직. (State machine, 엔진 정책 측정 평가, 응급 처리).
- `app/repositories/`: DB 연동 DAO 클래스.
- `app/schemas/`: API 입출력 및 MQTT 페이로드 데이터 검증용 Pydantic (v2) DTO.
- `app/workers/`: MQTT 메시지 수신 버퍼링, 멱등성 검사 및 MongoDB 비동기 Ingestion 데몬.

## 핵심 역할
수십에서 수천 대의 디바이스로부터 올라오는 MQTT Telemetry 페이로드(1Hz 주기)를 안정적으로 수집합니다. 정규화 및 `deviceId`+`rideId`+`seq`를 통한 멱등성을 지키며 데이터를 저장하고, 위험 알림 및 통제 명령을 처리합니다.
