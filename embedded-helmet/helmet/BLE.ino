#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const int BUZZER_PIN = 2;
const int FSR_L_PIN = A0;
const int FSR_R_PIN = A1;
const int PRES_THR = 300;
const int BAL_TOL = 150;
const long CONFIRM_MS = 2000;
const float CRASH_THR = 4.0;
const float FALL_THR = 0.8;

unsigned long wearStart = 0;
bool isWearing = false;

/* ===========================================================
   [BLE Layer: 프로토콜 및 페이로드 인코딩]
   =========================================================== */
// 1. 확장성: 서버 계약 변경 대비 스키마 버전
const uint8_t SCHEMA_VERSION = 1; 
const uint32_t CURRENT_RIDE_ID = 1004; // 호환성: rideId

// 2. 호환성: 서버 필수 필드를 포함한 이벤트 페이로드 구조체 (인코딩 대상)
struct SafetyEventPayload {
  uint8_t schemaVersion; // 확장성 분기점
  uint16_t seq;          // 호환성: 순번 (seq)
  uint32_t timestamp;    // 호환성: 시간 (timestamp)
  uint32_t rideId;       // 호환성: 라이딩 식별 (rideId)
  uint8_t eventLabel;    // 데이터: 사고 라벨 (1: 전도, 2: 충돌)
};

uint16_t globalEventSeq = 0; // 이벤트 순번 관리용

// BLE 설정
const char* SVC_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214";
const char* ST_UUID  = "19B10001-E8F2-537E-4F6C-D104768A1214"; 
const char* EV_UUID  = "19B10002-E8F2-537E-4F6C-D104768A1214"; 

BLEService helmetSvc(SVC_UUID);
BLEByteCharacteristic statusChar(ST_UUID, BLERead | BLENotify);
// 가변 바이트 전송을 위한 특성 설정 (구조체 크기만큼)
BLECharacteristic eventChar(EV_UUID, BLERead | BLENotify, sizeof(SafetyEventPayload));

/* ===========================================================
   [BLE Layer: 연결 관리 및 가시성]
   =========================================================== */
void onBLEConnected(BLEDevice central) {
  // 가시성: 연결 로그 남김
  Serial.print("Event: Connected to Central: ");
  Serial.println(central.address());
}

void onBLEDisconnected(BLEDevice central) {
  // 가시성: 연결 해제 로그 남김
  Serial.print("Event: Disconnected from Central: ");
  Serial.println(central.address());
}

void setup() {
  Serial.begin(9600);
  pinMode(BUZZER_PIN, OUTPUT);

  if (!IMU.begin() || !BLE.begin()) {
    Serial.println("Init Error");
    while (1);
  }

  // 연결 관리 이벤트 핸들러 등록
  BLE.setLocalName("Helmet_Module");
  BLE.setAdvertisedService(helmetSvc);
  BLE.setEventHandler(BLEConnected, onBLEConnected);
  BLE.setEventHandler(BLEDisconnected, onBLEDisconnected);
  
  helmetSvc.addCharacteristic(statusChar);
  helmetSvc.addCharacteristic(eventChar);
  BLE.addService(helmetSvc);
  
  statusChar.writeValue(0);
  BLE.advertise();
}

void loop() {
  BLE.poll(); // 연결 상태 유지 및 핸들러 처리

  // 1. 센서값 읽기
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) { IMU.readAcceleration(ax, ay, az); }

  // 2. 착용 판별
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true;
      statusChar.writeValue(1);
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false;
      statusChar.writeValue(0);
    }
  }

  // 3. 사고 감지 및 페이로드 인코딩 전송 (연계 영역)
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  if (impact > CRASH_THR) {
    sendEncodedEvent(2); // 충돌 인코딩 전송
    tone(BUZZER_PIN, 2000, 500);
  } 
  else if (abs(ax) > FALL_THR && isWearing) {
    sendEncodedEvent(1); // 전도 인코딩 전송
    tone(BUZZER_PIN, 1000, 500);
  }

  delay(100);
}

/* ===========================================================
   [BLE Layer: 페이로드 인코딩 및 전송 인터페이스]
   =========================================================== */
void sendEncodedEvent(uint8_t label) {
  SafetyEventPayload payload;
  
  // 페이로드 구성 (인코딩)
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;    // 순차적 번호 부여
  payload.timestamp = millis();      // 발생 시간 기록
  payload.rideId = CURRENT_RIDE_ID;  // 현재 세션 ID
  payload.eventLabel = label;        // 사고 종류

  // 바이너리 데이터로 변환하여 BLE 전송
  eventChar.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload));
  
  // 가시성: 로컬 로그
  Serial.print("Protocol: Event Sent - Seq: ");
  Serial.println(payload.seq);
}