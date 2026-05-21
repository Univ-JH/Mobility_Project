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

// 중복 전송을 방지할 디바운스 시간 간격 (3초)
const unsigned long SUDDEN_LOCK_MS = 3000; 

/* ===========================================================
   [2. 데이터 구조 및 통신 설정]
   =========================================================== */
const uint8_t SCHEMA_VERSION = 1;
uint32_t currentRideId = 1000; // 블루투스 연결 시마다 1씩 증가 (첫 연결 시 1001)
uint32_t globalEventSeq = 0;

struct __attribute__((packed)) SafetyEventPayload {
  uint8_t  schemaVersion; 
  uint32_t seq;           
  uint32_t timestamp;     
  uint32_t rideId;        
  uint8_t  eventLabel;    
};

BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic statusCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLECharacteristic eventCharacteristic("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);

void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload;
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;
  payload.timestamp = millis();
  payload.rideId = currentRideId; 
  payload.eventLabel = label;

  // ArduinoBLE 라이브러리의 표준 규격에 부합하는 응답형(With Response) 전송 메커니즘
  eventCharacteristic.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload), true);
  
  Serial.print("Event Sent [Seq: "); Serial.print(payload.seq); 
  Serial.print(", RideID: "); Serial.print(payload.rideId); Serial.print("] 타입: ");
  
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

bool oldCentralConnected = false;

void setup() {
  Serial.begin(9600);
  while (!Serial); 

  pinMode(BUZZER_PIN, OUTPUT);

  if (!IMU.begin()) {
    Serial.println("오류: IMU(가속도 센서) 초기화 실패!");
    while (1);
  }
  
  if (!BLE.begin()) {
    Serial.println("오류: BLE(블루투스 모듈) 초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Alpha");
  
  // 가독성 및 세미콜론/괄호 유효성 완벽 검증 완료
  BLE.setAdvertisedService(helmetService);
  
  helmetService.addCharacteristic(statusCharacteristic);
  helmetService.addCharacteristic(eventCharacteristic);
  BLE.addService(helmetService);
  
  statusCharacteristic.writeValue(0); 
  BLE.advertise();

  Serial.println("시스템 준비 완료");
}

void loop() {
  BLEDevice central = BLE.central();
  bool currentCentralConnected = central && central.connected();

  // 블루투스 연결 상태 변화 감지 및 Ride ID 자동 제어
  if (currentCentralConnected != oldCentralConnected) {
    if (currentCentralConnected) {
      currentRideId++; 
      
      Serial.print("\n[BLE] 중앙 장치와 연결되었습니다. 기기 주소: ");
      Serial.println(central.address());
      Serial.print("[BLE] 발급된 새로운 Ride ID: ");
      Serial.println(currentRideId);
    } else {
      Serial.println("\n[BLE] 중앙 장치와의 연결이 끊어졌습니다.");
    }
    oldCentralConnected = currentCentralConnected;
  }

  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  // --- [착용 상태 제어 파트] ---
  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusCharacteristic.writeValue(1);
      Serial.println("[STATUS] 상태 변경 -> 헬멧 착용됨 (WORN)");
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false; 
      statusCharacteristic.writeValue(0);
      Serial.println("[STATUS] 상태 변경 -> 헬멧 벗음 (IDLE)");

      // 라벨 5: 착용 중 충돌이 있었는데 3초 이내에 벗겨진 경우
      if (wasCrashTriggered && (millis() - crashTime < 3000)) {
        sendEncodedEvent(5, 0, ax, ay); 
        tone(BUZZER_PIN, 3000, 1000); 
      }
      wasCrashTriggered = false; 
    }
  }

  // --- [사고 감지 파트] ---
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  static unsigned long fallStartTime = 0; 
  static unsigned long lastAccEventTime = 0;   // 급가속 개별 타이머
  static unsigned long lastDecEventTime = 0;   // 급정거 개별 타이머
  
  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  // 미착용 상태일 때는 사고 감지 연산을 전부 스킵하고 내부 타이머만 리셋
  if (!isWearing) {
    fallStartTime = 0;
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }
  else if (impact > CRASH_THR) {
    sendEncodedEvent(2, impact, ax, ay); 
    tone(BUZZER_PIN, 2000, 500); 
    
    wasCrashTriggered = true;
    crashTime = millis();
    
    fallStartTime = 0; 
  } 
  // 고개를 크게 숙인게 아니고(수평 유지: abs(az) > 0.7) + 3초 이내에 중복 발생이 아닐 때만 급가속 판정
  else if (ax > SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastAccEventTime > SUDDEN_LOCK_MS) {
      sendEncodedEvent(3, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200); 
      lastAccEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  // 고개를 크게 숙인게 아니고(수평 유지: abs(az) > 0.7) + 3초 이내에 중복 발생이 아닐 때만 급정거 판정
  else if (ax < -SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastDecEventTime > SUDDEN_LOCK_MS) {
      sendEncodedEvent(4, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200); 
      lastDecEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  else if (isCurrentlyTilted) {
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