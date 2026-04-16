# 🛴 이동장치 안전 주행 시스템 (Safe Mobility System)

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

2륜 개인형 이동장치(전동킥보드, 자전거 등) 탑승자의 안전을 보장하기 위한 **스마트 헬멧 통합 안전 주행 제어 시스템** 프로젝트 리포지토리입니다.

## 🎯 핵심 기능 (Key Features)

1. **스마트 헬멧 감지**: 압력 감지 및 히스테리시스 로직을 이용해 헬멧의 올바른 착용 유무 판단 (안쓰면 출발 불가 제한)
2. **사고/응급 상황 감지**: 헬멧의 IMU 센서(가속도/기울기)를 활용해 충격 및 비정상 자세를 인식하여 사고로 판명 시 즉각 서버로 보고
3. **인도/차도 구분 판별 AI**: 하향 카메라가 측정한 노면 이미지를 Edge AI (Raspberry Pi) 경량 분류 모델이 분석하여 인도/차도 상태 파악
4. **자동 제동 시스템**: 인도 주행 등 위험/불법 지역 진입 시, 서보 모터를 통해 물리적으로 감속/제동하는 자동 안전 조치
5. **실시간 모니터링**: 
   - 보호자 및 관리자 관제 시스템: `웹 대시보드`
   - 디바이스 소유자/사용자 인터페이스: `모바일 애플리케이션`

---

## 🏗 시스템 구성 (Architecture)

시스템은 아래의 역할별 핵심 계층(계층적 컴포넌트) 기반으로 나뉘어 동작합니다.

- **임베디드 계층 (Embedded Helmet)**: Arduino Nano 33 BLE (헬멧 센싱 및 BLE 전송)
- **에지 처리 계층 (Edge AI Pi)**: Raspberry Pi 5 (카메라 데이터 처리, 보행자/노면 파악 및 하드웨어 브레이크 서보 제어)
- **백엔드 서버 계층 (Backend Cloud)**: FastAPI + MQTT 워커 + MongoDB (대용량 텔레메트리/이벤트 수집, 정책 처리)
- **프론트엔드 환경 (Web & Mobile)**: React 대시보드, React Native 앱

## 📂 폴더 구조 (Project Structure)

각 폴더는 도메인 역할을 분담하며 세부적인 `README.md` 와 AI 개발 가이드인 `AGENTS.md`를 포함합니다.

| 분류 | 폴더명 | 설명 |
| :--- | :--- | :--- |
| **Backend** | [`backend/`](./backend/) | 이동장치와 통신하여 데이터를 분산 처리 및 측정하는 백엔드 서버 |
| **Edge** | [`edge-pi/`](./edge-pi/) | 킥보드/자전거에 부착되는 본체 Edge 처리 스크립트 모음 |
| **Embedded** | [`embedded-helmet/`](./embedded-helmet/) | 헬멧 내장형 센서 펌웨어 및 상태 송출 로직 |
| **Frontend** | [`frontend-mobile/`](./frontend-mobile/) | 사용자용 다이얼로그 및 정보/알람 확인 모바일 앱 소스 |
| **Frontend** | [`frontend-web/`](./frontend-web/) | 관리자/운영자용 중앙 관제 웹 대시보드 소스 |
| **Docs** | [`docs/`](./docs/) | 프로토콜 스펙 명세, 데이터 사전 및 매뉴얼 규정 |
| **Infra** | [`infra/`](./infra/) | AWS 퍼블릭 클라우드, Docker Compose 등 배포 관련 스크립트 |

---
## 📑 주요 기획/설계 원문 (Documentations)
세부적인 프로젝트 구조 및 S/W 아키텍처는 다음 문서를 직접 참고하세요.

- 전체 통합 시스템 기획 및 도메인 분석: `SAFE_MOBILITY_SYSTEM_PLAN.md`
- 백엔드/API 구체적 구현 상세 계획: `BACKEND_IMPLEMENTATION_PLAN.md`
- 시스템 전체 마스터 디자인 및 마일스톤: `PROJECT_MASTER_PLAN.md`

## 🤖 개발 공통 규칙 (For AI / Teammates)
팀원 및 협업하는 AI(개발 에이전트)는 본 시스템 작성 시 **무조건 Fail-Safe(불확실 시 감속/정지 상태로 전환)** 원칙과 **보안 안전 관측 원칙**을 지켜야 합니다. 전체 공통 규율은 리포지토리 루트의 `AGENTS.md`를, 개발용 상세 룰은 `.cursor/rules/` 폴더를 참조하세요.
