#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

/* ===========================================================
   [1. 하드웨어 설정 및 임계치 조정]
   =========================================================== */
const int BUZZER_PIN = 2;      
const int FSR_L_PIN = A0;      
const int FSR_R_PIN = A1;      

const int PRES_THR = 300;      
const int BAL_TOL = 150;       
const long CONFIRM_MS = 2000;  

const float CRASH_THR = 4.0;   
const float FALL_THR = 1.2;
const float SUDDEN_THR = 0.8;   // 급가속/급정거 임계치

/* ===========================================================
   [2. 데이터 구조 및 통신 설정]
   =========================================================== */
const uint8_t SCHEMA_VERSION = 1;
const uint32_t CURRENT_RIDE_ID = 1001;
uint32_t globalEventSeq = 0;

struct __attribute__((packed)) SafetyEventPayload {
  uint8_t  schemaVersion; 
  uint32_t seq;           
  uint32_t timestamp;     
  uint32_t rideId;        
  uint8_t  eventLabel;    
};

BLEService helmetSvc("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEIntCharacteristic statusChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLECharacteristic eventChar("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);

void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload;
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;
  payload.timestamp = millis();
  payload.rideId = CURRENT_RIDE_ID;
  payload.eventLabel = label;

  eventChar.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload));
  
  Serial.print("Event Sent [Seq: "); Serial.print(payload.seq); Serial.print("] 타입: ");
  
  switch(label) {
    case 1: Serial.print("EMERGENCY: 전도(Fall) | [확정값] "); break;
    case 2: Serial.print("EMERGENCY: 충돌(Crash) | [확정값] 충격량: "); Serial.print(impactG); Serial.println("G"); return;
    case 3: Serial.print("EMERGENCY: 급가속 | [확정값] "); break;
    case 4: Serial.print("EMERGENCY: 급정거 | [확정값] "); break;
    case 5: Serial.print("ALERT: 충돌 후 이탈 의심 (Crash to Idle) | [확정값] "); break;
  }
  Serial.print("X축(ax): "); Serial.print(ax); Serial.print("G, Y축(ay): "); Serial.print(ay); Serial.println("G");
}

/* ===========================================================
   [3. 초기 설정 및 메인 로직]
   =========================================================== */
unsigned long wearStart = 0;   
bool isWearing = false;        

bool wasCrashTriggered = false;
unsigned long crashTime = 0;

void setup() {
  Serial.begin(9600);
  
  // 시리얼 모니터가 켜질 때까지 아두이노 프로그램을 대기시킵니다.
  while (!Serial); 

  pinMode(BUZZER_PIN, OUTPUT);

  // 센서와 블루투스 중 어디서 문제가 발생하는지 개별 진단합니다.
  if (!IMU.begin()) {
    Serial.println("오류: IMU(가속도 센서) 초기화 실패!");
    while (1);
  }
  
  if (!BLE.begin()) {
    Serial.println("오류: BLE(블루투스 모듈) 초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet");
  BLE.setAdvertisedService(helmetSvc);
  helmetSvc.addCharacteristic(statusChar);
  helmetSvc.addCharacteristic(eventChar);
  BLE.addService(helmetSvc);
  statusChar.writeValue(0); 
  BLE.advertise();

  Serial.println("시스템 준비 완료: 급가/감속 0.5초 연속전송 방지 필터 적용");
}

void loop() {
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 착용 판별 로직
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  // --- [착용 상태 제어 파트] ---
  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusChar.writeValue(1);
      Serial.println("\n[STATUS] 상태 변경 -> 헬멧 착용됨 (WORN)");
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false; 
      statusChar.writeValue(0);
      Serial.println("\n[STATUS] 상태 변경 -> 헬멧 벗음 (IDLE)");

      // 충돌 발생 후 3초 이내에 미착용 상태로 바뀐 경우 5번 전송
      if (wasCrashTriggered && (millis() - crashTime < 3000)) {
        sendEncodedEvent(5, 0, ax, ay); 
        tone(BUZZER_PIN, 3000, 1000); // 의심 상태 경고음 출력
      }
      wasCrashTriggered = false; 
    }
  }

  // --- [사고 감지 파트] ---
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  static unsigned long fallStartTime = 0; 
  static unsigned long lastSuddenEventTime = 0; 
  
  // X, Y축 기울어짐과 Z축 반전(뒤집힘)을 모두 전도로 판단
  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  if (impact > CRASH_THR) {
    sendEncodedEvent(2, impact, ax, ay); 
    tone(BUZZER_PIN, 2000, 500);
    
    wasCrashTriggered = true;
    crashTime = millis();
    
    fallStartTime = 0; 
  } 
  else if (ax > SUDDEN_THR) {
    if (millis() - lastSuddenEventTime > 500) {
      sendEncodedEvent(3, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200);
      lastSuddenEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  else if (ax < -SUDDEN_THR) {
    if (millis() - lastSuddenEventTime > 500) {
      sendEncodedEvent(4, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200);
      lastSuddenEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  else if (isCurrentlyTilted && isWearing) {
    if (fallStartTime == 0) {
      fallStartTime = millis(); 
    }
    
    if (millis() - fallStartTime > 1500) {
      sendEncodedEvent(1, impact, ax, ay); 
      tone(BUZZER_PIN, 1000, 500);
      fallStartTime = millis(); 
    }
  }
  else {
    fallStartTime = 0;
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }

  delay(100); 
}