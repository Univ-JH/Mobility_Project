#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

/* ===========================================================
   [1. 하드웨어 설정 및 사고 판단 기준값]
   =========================================================== */
// 테스트용이므로 FSR_PIN은 사용하지 않습니다.

const int PRES_THR = 300;      // 착용 판정 기준 (센서 값이 300보다 커야 함)
const long CONFIRM_MS = 1000;  // 착용 확인 대기시간 (1초)
const long DETACH_MS = 3000;   // 벗음 확인 대기시간 (3초)

const float CRASH_THR = 4.0;   // 충돌 감지 기준 (4.0G 이상)
const float FALL_THR = 1.2;    // 전도(넘어짐) 감지 기준
const float SUDDEN_THR = 0.8;  // 급가속 및 급정거 판단 기준

// 똑같은 신호가 계속 연속으로 전송되는 것을 막아주는 제한 시간 (3초)
const unsigned long SUDDEN_LOCK_MS = 3000; 

/* ===========================================================
   [2. 데이터 구조 및 블루투스(BLE) 통신 설정]
   =========================================================== */
const uint8_t SCHEMA_VERSION = 1; // 데이터 설계도 버전 (1번으로 고정)
uint32_t currentRideId = 1000; // 블루투스가 새로 연결될 때마다 1씩 늘어나는 주행 번호
uint32_t globalEventSeq = 0;   // 몇 번째 사고 신호인지 알려주는 일련번호 (0, 1, 2...)

// 라즈베리파이로 쏠 14바이트짜리 데이터 상자 규격
struct __attribute__((packed)) SafetyEventPayload {
  uint8_t  schemaVersion; // 1바이트 (버전)
  uint32_t seq;           // 4바이트 (사고 번호)
  uint32_t timestamp;     // 4바이트 (아두이노가 켜진 후 흐른 시간)
  uint32_t rideId;        // 4바이트 (주행 세션 ID)
  uint8_t  eventLabel;    // 1바이트 (사고 종류 번호: 1~5)
};

// 블루투스 서비스 및 데이터 고유 주소(UUID) 설정
BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic statusCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLECharacteristic eventCharacteristic("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);

// [데이터 포장 및 전송 함수]
void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload; 
  
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;
  payload.timestamp = millis(); 
  payload.rideId = currentRideId; 
  payload.eventLabel = label;

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
   [3. 초기 설정]
   =========================================================== */
unsigned long wearStart = 0;   
unsigned long detachStart = 0; 
bool isWearing = false;        

bool wasCrashTriggered = false; 
unsigned long crashTime = 0;    

bool oldCentralConnected = false; 

void setup() {
  Serial.begin(9600);

  if (!IMU.begin()) {
    Serial.println("오류: IMU(가속도 센서) 초기화 실패!");
    while (1);
  }
  if (!BLE.begin()) {
    Serial.println("오류: BLE(블루투스 모듈) 초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Alpha");
  BLE.setAdvertisedService(helmetService);
  
  helmetService.addCharacteristic(statusCharacteristic);
  helmetService.addCharacteristic(eventCharacteristic);
  BLE.addService(helmetService);
  
  statusCharacteristic.writeValue(0); 
  BLE.advertise(); 

  Serial.println("시스템 준비 완료 (테스트 모드: 항상 착용 상태로 간주됨)");
}

/* ===========================================================
   [4. 메인 루프]
   =========================================================== */
void loop() {
  BLEDevice central = BLE.central();
  bool currentCentralConnected = central && central.connected();

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

  // ★★★ [테스트 핵심 수정 부분] ★★★
  // 압력 센서가 없으므로 아날로그 핀을 읽는 대신 항상 임계치(300)보다 높은 400을 강제로 주입합니다.
  int fsrValue = 400; 
  
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  bool isPressed = (fsrValue > PRES_THR); // 무조건 true가 됨

  // --- [착용 상태 제어 파트] ---
  if (isPressed) {
    detachStart = 0; 
    
    if (wearStart == 0) wearStart = millis(); 
    
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusCharacteristic.writeValue(1); 
      Serial.println("[STATUS] 상태 변경 -> 헬멧 착용됨 (테스트용 자동 WORN)");
    }
  } 
  else {
    // fsrValue를 400으로 고정했기 때문에 이 부분은 테스트 중에 타지 않습니다.
    // (이탈 의심 5번 테스트를 하려면 코드에서 fsrValue = 0; 으로 수정 후 업로드해야 합니다.)
    wearStart = 0; 
    
    if (isWearing) {
      if (detachStart == 0) detachStart = millis(); 
      
      if (millis() - detachStart > DETACH_MS) {
        isWearing = false; 
        detachStart = 0; 
        statusCharacteristic.writeValue(0); 
        Serial.println("[STATUS] 상태 변경 -> 헬멧 벗음 (IDLE)");

        if (wasCrashTriggered && (millis() - crashTime < 3000)) {
          sendEncodedEvent(5, 0, ax, ay); 
        }
        wasCrashTriggered = false; 
      }
    } else {
      detachStart = 0; 
    }
  }

  // --- [사고 감지 파트] ---
  float impact = sqrt(ax*ax + ay*ay + az*az); 
  
  static unsigned long fallStartTime = 0;    
  static unsigned long lastAccEventTime = 0;   
  static unsigned long lastDecEventTime = 0;   
  
  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  if (!isWearing) {
    fallStartTime = 0;
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }
  else if (impact > CRASH_THR) {
    sendEncodedEvent(2, impact, ax, ay); 
    
    wasCrashTriggered = true; 
    crashTime = millis();     
    
    fallStartTime = 0; 
  } 
  else if (ax > SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastAccEventTime > SUDDEN_LOCK_MS) { 
      sendEncodedEvent(3, impact, ax, ay); 
      lastAccEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  else if (ax < -SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastDecEventTime > SUDDEN_LOCK_MS) { 
      sendEncodedEvent(4, impact, ax, ay); 
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