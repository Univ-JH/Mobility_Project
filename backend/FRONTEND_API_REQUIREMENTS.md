# 📡 프론트엔드 연동을 위한 백엔드 API 명세 요구사항 (Frontend API Requirements)

본 문서는 **모바일 앱(사용자용)**과 **웹 대시보드(관리자용)** 프론트엔드의 화면 및 기능을 분석하여, 백엔드에서 필수적으로 구현해야 할 REST API 목록을 정리한 문서입니다. (참고: 실시간 주행 상태 데이터 등은 MQTT를 통해 별도로 스트리밍 처리됨을 전제로 합니다.)

---

## 📱 1. 모바일 앱 (User App) 요구 API

사용자의 앱 이용, 기기 페어링 및 프로필 관리를 위해 필요한 API입니다.

### 사용자 및 인증
* **`POST /api/v1/auth/login`**
  * **기능:** 모바일 앱 사용자 로그인 및 JWT 토큰 발급
* **`GET /api/v1/users/profile`**
  * **기능:** 로그인한 사용자의 기본 프로필 정보, 종합 안전 점수(Safety Score), 앱 설정 정보 조회
* **`GET /api/v1/users/history`**
  * **기능:** 사용자의 과거 주행 이력 리스트(시간, 거리, 주요 알림 발생 건수 등) 조회

### 디바이스 페어링 및 제어
* **`POST /api/v1/devices/pair`**
  * **기능:** 모바일 앱에서 BLE를 통해 인식한 새로운 기기(PI-Alpha 등)를 사용자 계정에 등록 및 매핑
* **`GET /api/v1/devices/{device_id}/status`**
  * **기능:** 연결된 기기의 최신 상태 정보(잠금 여부, 배터리 상태, 헬멧 착용 상태)를 폴백(Fallback) 용도로 조회 (주로 MQTT를 사용하나 초기 로드 시 REST 사용)
* **`POST /api/v1/devices/{device_id}/unlock`**
  * **기능:** 모바일 앱의 명령을 통해 킥보드/자전거의 잠금을 해제(시동)

### 이벤트 및 긴급 상황
* **`POST /api/v1/events/emergency`**
  * **기능:** 앱 내 "Simulate Crash" 또는 실제 응급 상황 발생 시 사용자 앱이 직접 서버로 긴급 구조 신호(SOS)를 발송

---

## 💻 2. 웹 관리자 대시보드 (Admin Web) 요구 API

관리자가 전체 모빌리티 기기의 현황을 모니터링하고 분석하기 위해 필요한 API입니다.

### 종합 통계 및 요약 지표
* **`GET /api/v1/admin/stats`**
  * **기능:** 대시보드 최상단의 요약 수치 데이터 제공
  * **반환 항목:** 전체 활성 디바이스 수(`activeDevices`), 금일 응급 상황 발생 건수(`emergenciesToday`), 평균 헬멧 준수율(`helmetCompliance`), 전체 평균 배터리 잔량(`avgBattery`)

### 실시간 관제 및 지도
* **`GET /api/v1/admin/devices/locations`**
  * **기능:** 현재 활성화되어 주행 중인 모든 디바이스의 최신 GPS 좌표 데이터 목록 반환 (Map Pin 렌더링용)

### 차트 데이터 (분석)
* **`GET /api/v1/admin/analytics/alerts-timeline`**
  * **기능:** 오늘 하루(또는 특정 기간) 동안 발생한 시간대별 경고 및 알림 횟수 반환 (Area Chart 렌더링용)
* **`GET /api/v1/admin/analytics/environment`**
  * **기능:** 현재 주행 중인 기기들의 노면 상태 비율(안전한 차도 vs 인도 주행) 통계 반환 (Pie Chart 렌더링용)

### 이벤트 로그 관리
* **`GET /api/v1/admin/events`**
  * **기능:** 최근 발생한 디바이스 시스템 로그 및 이벤트 리스트 조회 (Pagination 및 필터링 적용)
  * **반환 항목:** Event ID, Device명, Type(EMERGENCY, WARNING 등), Reason, Time, Severity
* **`GET /api/v1/admin/export/logs`**
  * **기능:** 대시보드의 "Export Logs" 버튼 클릭 시, 조회 가능한 전체 혹은 조건별 로그 데이터를 CSV 형식으로 다운로드할 수 있는 파일/스트림 반환

---

## 📌 추가 고려사항
1. 모든 API 응답은 일관된 JSON 포맷을 유지해야 합니다 (예: `{ "status": "success", "data": {...}, "message": null }`).
2. 관리자 웹 API는 관리자 권한 인증(Admin Role)이 포함된 토큰을 검증하는 미들웨어를 거쳐야 합니다.
3. 시뮬레이션 및 Mockup 개발 단계를 고려하여, API 개발 전 Swagger/Redoc 등을 통한 명세서 선제공이 권장됩니다.
