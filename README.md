# Mobility Project

2륜 개인형 이동장치(전동킥보드/자전거 등) 대상 **안전 주행 + 헬멧 착용 감지 + 자동 속도 제어** 시스템의 캡스톤 프로젝트 리포지토리.

## 문서/규칙
- 안전/요구사항/아키텍처: `SAFE_MOBILITY_SYSTEM_PLAN.md`
- 백엔드 구현 계획: `BACKEND_IMPLEMENTATION_PLAN.md`
- 개발 규칙(공통): `AGENTS.md`
- Cursor 코드 규칙: `.cursor/rules/`

## 폴더 개요
- `backend/`: FastAPI + MQTT ingestion + MongoDB 저장/조회 + 정책/응급 엔진
- `frontend-web/`: React 웹 대시보드/관리 UI
- `frontend-mobile/`: React Native 모바일 앱(실시간 상태/알림)
- `edge-pi/`: Raspberry Pi 5 엣지(카메라/AI 추론/제동 제어)
- `embedded-helmet/`: Arduino Nano 33 BLE(압력/IMU 이벤트 생성, BLE 송신)
- `infra/`: 브로커/DB/배포 구성 문서(예: Docker, 네트워크, 운영 런북 연결)
- `docs/`: 추가 명세/계약 문서(스키마, 런북, 데이터 사전)

## 개발 원칙(구현 전)
- MQTT payload와 API DTO는 v1 스키마 계약을 기준으로 고정한다.
- 상태 전이/이벤트/제어 명령은 관측 가능해야 한다(`traceId`, `rideId` 등).
- 불확실하면 Fail-Safe(제한/감속/정지)로 수렴한다.

