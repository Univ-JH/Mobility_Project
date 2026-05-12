#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

/* ===========================================================
   [1. 하드웨어 설정 및 임계치]
   =========================================================== */
const int BUZZER_PIN = 2;      // 경고 알람용 부저 핀
const int FSR_L_PIN = A0;      // 왼쪽 압력 센서
const int FSR_R_PIN = A1;      // 오른쪽 압력 센서

const int PRES_THR = 300;      // 착용 판단 압력 임계치
const int BAL_TOL = 150;       // 좌우 센서 균형 오차
const long CONFIRM_MS = 2000;  // WORN 상태 확정 대기 시간 (2초)

const float CRASH_THR = 4.0;   // 충돌 판단 가속도
const float FALL_THR = 0.9;    // 전도 판단 기울기
const float SUDDEN_THR = 1.5;  // 급가속/급정거 판단 임계치

/* ===========================================================
   [2. 데이터 구조 및 통신 설정]
   =========================================================== */
const uint8_t SCHEMA_VERSION = 1;
const uint32_t CURRENT_RIDE_ID = 1001;
uint32_t globalEventSeq = 0;

// 속도 필드를 제거하여 패킷을 14바이트로 최적화
struct __attribute__((packed)) SafetyEventPayload {
  uint8_t  schemaVersion; // 1 byte
  uint32_t seq;           // 4 bytes
  uint32_t timestamp;     // 4 bytes
  uint32_t rideId;        // 4 bytes
  uint8_t  eventLabel;    // 1 byte
};

BLEService helmetSvc("19B10000-E8F2-537E-4F6C-D104768A1214");
// 착용 상태 전송용 (0: IDLE, 1: WORN)
BLEIntCharacteristic statusChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
// 사고 이벤트 전송용 (14바이트)
BLECharacteristic eventChar("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);

/* ===========================================================
   [3. 데이터 전송 함수]
   =========================================================== */
void sendEncodedEvent(uint8_t label) {
  SafetyEventPayload payload;
  
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;
  payload.timestamp = millis();
  payload.rideId = CURRENT_RIDE_ID;
  payload.eventLabel = label;

  eventChar.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload));
  
  Serial.print("Event Sent [Seq: ");
  Serial.print(payload.seq);
  Serial.print("] 타입: ");
  
  switch(label) {
    case 1: Serial.println("EMERGENCY: 전도(Fall)"); break;
    case 2: Serial.println("EMERGENCY: 충돌(Crash)"); break;
    case 3: Serial.println("EMERGENCY: 급가속"); break;
    case 4: Serial.println("EMERGENCY: 급정거"); break;
  }
}

/* ===========================================================
   [4. 초기 설정 및 메인 로직]
   =========================================================== */
unsigned long wearStart = 0;   
bool isWearing = false;        

void setup() {
  Serial.begin(9600);
  pinMode(BUZZER_PIN, OUTPUT);

  if (!IMU.begin() || !BLE.begin()) {
    Serial.println("하드웨어 초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet");
  BLE.setAdvertisedService(helmetSvc);
  helmetSvc.addCharacteristic(statusChar);
  helmetSvc.addCharacteristic(eventChar);
  BLE.addService(helmetSvc);
  
  statusChar.writeValue(0); // 초기 상태 IDLE
  BLE.advertise();

  Serial.println("시스템 준비 완료: 속도 계산 기능 제외");
}

void loop() {
  // 1. 센서 데이터 수집
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 2. 상태 전이 로직: IDLE <-> WORN
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusChar.writeValue(1);
      Serial.println("상태 변경: WORN (착용됨)");
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false; 
      statusChar.writeValue(0);
      Serial.println("상태 변경: IDLE (미착용)");
    }
  }

  // 3. 사고 감지 (EMERGENCY)
  // 가속도의 합산 벡터 값을 이용한 충격량 계산
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  if (impact > CRASH_THR) {
    sendEncodedEvent(2); // 충돌
    tone(BUZZER_PIN, 2000, 500);
  } 
  else if (ax > SUDDEN_THR) {
    sendEncodedEvent(3); // 급가속
    tone(BUZZER_PIN, 1500, 200);
  }
  else if (ax < -SUDDEN_THR) {
    sendEncodedEvent(4); // 급정거
    tone(BUZZER_PIN, 1500, 200);
  }
  else if ((abs(ax) > FALL_THR || abs(ay) > FALL_THR) && isWearing) {
    sendEncodedEvent(1); // 전도
    tone(BUZZER_PIN, 1000, 500);
  }

  delay(100); 
}