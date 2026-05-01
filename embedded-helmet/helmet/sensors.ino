#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

/* ===========================================================
   [가시성/명확성] 필터 및 임계치 상수 정의 (최상단 분리)
   =========================================================== */
// 1. 하드웨어 핀 설정
const int FSR_L_PIN = A0;
const int FSR_R_PIN = A1;
const int BUZZER_PIN = 2;

// 2. 압력 센서 필터 및 임계치
const int PRES_THR = 300;       // 압력 판단 기준 (Threshold)
const int BAL_TOL = 150;        // 좌우 균형 허용 오차 (Tolerance)
const long CONFIRM_MS = 2000;   // 상태 확정 필터 시간 (2초)

// 3. IMU 사고 감지 임계치
const float CRASH_THR = 4.0;    // 충돌 감지 가속도 특징값 (G)
const float FALL_THR = 0.8;     // 전도 감지 기울기 특징값 (G)

/* ===========================================================
   [호환성] BLE Payload와 1:1 대응하는 출력 지표 (라벨)
   =========================================================== */
enum DeviceStatus { UNWORN = 0, WORN = 1 };
enum AccidentEvent { NONE = 0, FALL = 1, CRASH = 2 };

/* ===========================================================
   [전역 상태 변수]
   =========================================================== */
unsigned long wearStart = 0;
bool isWearing = false;

// 센서 특징 데이터 (필터링된 결과값)
struct SensorFeatures {
  int fsrL;
  int fsrR;
  float ax, ay, az;
  float impact; // 가속도 벡터 합
} currentFeature;

void setup() {
  Serial.begin(9600);
  pinMode(BUZZER_PIN, OUTPUT);

  if (!IMU.begin() || !BLE.begin()) {
    Serial.println("Sensor/BLE Init Failed");
    while (1);
  }
  
  // (이후 BLE 서비스 설정 및 시작 로직...)
}

void loop() {
  // 1. 데이터 취득 및 특징 추출 (Input Feature Extraction)
  updateSensorFeatures();

  // 2. 필터링 및 이벤트 매핑 (Logic Mapping)
  processWearingDetection();
  processAccidentDetection();

  delay(100); 
}

/* ===========================================================
   [확장성] 센서 입력 특징 추출 영역
   (센서 교체 시 이 함수 내부의 매핑만 조정하면 됩니다)
   =========================================================== */
void updateSensorFeatures() {
  // 압력 데이터 취득
  currentFeature.fsrL = analogRead(FSR_L_PIN);
  currentFeature.fsrR = analogRead(FSR_R_PIN);

  // IMU 데이터 취득 및 특징량(Impact) 계산
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(currentFeature.ax, currentFeature.ay, currentFeature.az);
    // 충격량 특징 추출: $$impact = \sqrt{ax^2 + ay^2 + az^2}$$
    currentFeature.impact = sqrt(pow(currentFeature.ax, 2) + pow(currentFeature.ay, 2) + pow(currentFeature.az, 2));
  }
}

/* ===========================================================
   [확장성/호환성] 입력 특징 -> 이벤트 라벨 매핑 및 출력 인터페이스
   =========================================================== */

// 착용 여부 필터링 및 상태 생성
void processWearingDetection() {
  // 입력 특징 분석
  bool isPressed = (currentFeature.fsrL > PRES_THR) && (currentFeature.fsrR > PRES_THR);
  bool isBalanced = abs(currentFeature.fsrL - currentFeature.fsrR) < BAL_TOL;

  // 히스테리시스 필터링 (시간 지연 확정)
  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true;
      triggerStatusChangeEvent(WORN); // 상위 인터페이스 호출
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false;
      triggerStatusChangeEvent(UNWORN); // 상위 인터페이스 호출
    }
  }
}

// 사고 의심 이벤트 매핑
void processAccidentDetection() {
  // 충돌 특징 분석 (G값 임계치 비교)
  if (currentFeature.impact > CRASH_THR) {
    triggerAccidentEvent(CRASH); // 상위 인터페이스 호출
  } 
  // 전도 특징 분석 (기울기 및 착용 여부 조합)
  else if (abs(currentFeature.ax) > FALL_THR && isWearing) {
    triggerAccidentEvent(FALL); // 상위 인터페이스 호출
  }
}

/* ===========================================================
   [상위 인터페이스] 이벤트 생성 및 BLE Payload 연동 영역
   =========================================================== */
void triggerStatusChangeEvent(DeviceStatus status) {
  // BLE payload 의미와 1:1 대응 (WORN=1, UNWORN=0)
  // statusChar.writeValue(status); 
  Serial.print("Status Changed: ");
  Serial.println(status == WORN ? "WORN" : "UNWORN");
}

void triggerAccidentEvent(AccidentEvent event) {
  // BLE payload 의미와 1:1 대응 (FALL=1, CRASH=2)
  // eventChar.writeValue(event);
  
  if (event == CRASH) {
    tone(BUZZER_PIN, 2000, 500);
    Serial.println("Event: CRASH Detected");
  } else if (event == FALL) {
    tone(BUZZER_PIN, 1000, 500);
    Serial.println("Event: FALL Detected");
  }
}