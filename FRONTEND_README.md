# 🛴 이동장치 안전 주행 시스템 - 프론트엔드 상세 가이드 (Frontend Guide)

본 문서는 **이동장치 안전 주행 시스템 (Safe Mobility System)**의 프론트엔드 구조와 주요 기능들을 상세히 정의한 가이드 문서입니다. 본 시스템의 프론트엔드는 사용자를 위한 **모바일 애플리케이션(React Native)**과 관리자를 위한 **웹 대시보드(React + Vite)**로 분리되어 구축되었습니다.

---

## 📱 1. 모바일 애플리케이션 (Frontend Mobile)

모바일 앱은 개인형 이동장치 사용자가 주행 전 기기를 페어링하고, 주행 중 실시간 안전 상태를 모니터링하며, 응급 상황을 확인/조치할 수 있는 사용자 인터페이스를 제공합니다.

### 🛠 기술 스택
* **프레임워크:** React Native (Expo)
* **라우팅:** Expo Router (파일 기반 라우팅)
* **아이콘 및 UI:** lucide-react-native
* **주요 통신(예정):** BLE (기기 페어링용), MQTT (실시간 텔레메트리), REST API (프로필 및 히스토리 조회)

### 📂 주요 화면 및 기능 구조

1. **온보딩 화면 (`app/index.tsx`)**
   * 앱 실행 시 최초로 노출되는 화면입니다.
   * 안전 주행 시스템의 핵심 가치와 사용법을 안내하며, 페어링 화면이나 대시보드로 진입할 수 있는 분기점 역할을 합니다.

2. **디바이스 페어링 화면 (`app/pairing.tsx`)**
   * 탑승자가 헬멧 및 킥보드/자전거에 부착된 제어 장치(Raspberry Pi / Arduino)와 연결하는 화면입니다.
   * Bluetooth(BLE)를 활용한 주변 기기 스캔 및 연결 시뮬레이션을 제공하며, 성공적인 연결 후 메인 대시보드로 이동합니다.

3. **메인 대시보드 (`app/(tabs)/dashboard.tsx`)**
   * **실시간 상태 모니터링:** 헬멧 착용 여부(WORN/UNWORN) 및 이동장치 잠금 상태(Locked/Active)를 실시간으로 표시합니다.
   * **주행 환경 감지 UI:** 현재 노면 상태가 '안전한 차도(Safe Road)'인지 '인도(Sidewalk Detected)'인지 시각적으로 피드백합니다.
   * **응급 상황 시뮬레이터:** "Simulate Crash" 버튼을 통해 사고 발생 시의 긴급 경고 팝업 및 처리 프로세스를 검증할 수 있습니다.

4. **사용자 프로필 (`app/(tabs)/profile.tsx`)**
   * 사용자의 종합 안전 점수(Safety Score)와 최근 주행 이력을 확인합니다.
   * 계정 설정 및 앱 환경설정 기능을 제공합니다.

---

## 💻 2. 웹 관리자 대시보드 (Frontend Web)

웹 대시보드는 전체 모빌리티 기기의 운영 현황, 사고 발생 알림, 사용자 헬멧 착용 준수율 등을 관리자가 한눈에 파악하고 통제할 수 있는 중앙 관제 인터페이스입니다.

### 🛠 기술 스택
* **프레임워크:** React (Vite 기반) + TypeScript
* **데이터 시각화:** Recharts (다양한 통계 차트 구현)
* **아이콘 및 UI:** lucide-react, Vanilla CSS 기반의 모던 다크 테마

### 📂 주요 화면 및 기능 구조 (`src/screens/Dashboard.tsx`)

1. **헤더 및 퀵 액션 (Header Actions)**
   * **기능:** 실시간 데이터 수동 새로고침 및 이벤트 로그 데이터 내보내기(Export) 기능을 지원합니다.

2. **핵심 요약 지표 (Stats Overview)**
   * 전체 시스템의 활성 디바이스 수 (Active Devices)
   * 금일 발생한 응급/사고 상황 건수 (Emergencies Today)
   * 전체 사용자의 헬멧 착용 준수율 (Helmet Compliance %)
   * 기기들의 평균 배터리 잔량 (Avg Battery %)

3. **라이브 지도 트래킹 (Live Device Tracking)**
   * 맵뷰 상에 현재 운용 중인 디바이스들의 실시간 위치를 시각화합니다.
   * (향후 AWS Location Services 등과 연동되어 정확한 지도 매핑을 수행합니다.)

4. **데이터 시각화 차트 (Analytics Charts)**
   * **Alerts Timeline (Area Chart):** 시간대별로 발생한 경고 및 이벤트 추이를 꺾은선(영역) 차트로 표시하여 위험 시간대를 분석합니다.
   * **Riding Environment (Pie Chart):** 수집된 도로 주행(Road) 대 인도 주행(Sidewalk) 비율을 파이 차트로 보여주어 인프라 정책 마련에 기여합니다.

5. **실시간 이벤트 로그 (Recent Device Logs)**
   * 이벤트 ID, 발생 기기, 이벤트 타입(EMERGENCY, WARNING, INFO 등), 세부 사유(Crash Detected, No Helmet 등), 발생 시간 및 중요도(Severity)를 표 형태로 나열합니다.

---

## 🔄 3. 프론트엔드 아키텍처 및 통신 전략

프론트엔드의 화면들은 프로토타입 단계에서는 Mock Data를 기반으로 동작하지만, 운영 환경(Production)으로 전환 시 다음 통신 전략을 따릅니다.

1. **실시간 텔레메트리 (MQTT/WebSocket):** 이동장치의 주행 상태, 헬멧 착용 여부, 응급 경고 등 1초 미만의 지연 시간이 요구되는 데이터는 MQTT 프로토콜을 통해 AWS IoT Broker에서 직접 구독하여 화면에 반영합니다.
2. **이력 및 통계 조회 (REST API):** 프로필 정보, 주행 히스토리, 관리자용 일간 통계 분석, 기기 목록 등은 Backend(FastAPI 등) 서버로 RESTful HTTP 요청을 보내어 데이터를 동기화합니다.
3. **엣지 디바이스 직접 연결 (BLE):** 모바일 앱에서의 초기 장비 페어링 및 근거리 인증 과정은 Bluetooth 통신으로 이루어집니다.
