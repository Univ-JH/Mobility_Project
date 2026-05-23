#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const int BUZZER_PIN = 2;      
const int FSR_L_PIN = A0;      
const int FSR_R_PIN = A1;      

const int PRES_THR = 300;      // FSR(압력센서) 착용 판정 최소 임계값
const int BAL_TOL = 150;       // 좌우 압력 차이 허용치 (기울어짐 오판 방지)
const long CONFIRM_MS = 2000;  // 헬멧을 완전히 썼다고 판정할 대기 시간 (2초)

const float CRASH_THR = 4.0;   // 충돌 감지 임계값 (4.0G 이상 대형 충격)
const float FALL_THR = 1.2;    // 좌우 전도(넘어짐) 판단 가속도 임계값
const float SUDDEN_THR = 0.8;  // 앞뒤 급가속/급정거 판단 가속도 임계값

const unsigned long SUDDEN_LOCK_MS = 3000; // 급가속/급정거 이벤트 간 3초간의 중복 전송 방지 시간

uint32_t currentRideId = 1000; // 주행 세션 ID (중앙 장치 연결 시마다 +1)
uint32_t globalEventSeq = 0;   // 이벤트 패킷 순서 번호 (누락 검증용)

// [구조체 정렬 패킹] 총 13바이트 규격 데이터셋
struct __attribute__((packed)) SafetyEventPayload {
  uint32_t seq;           // 4바이트
  uint32_t timestamp;     // 4바이트 (아두이노 가동 후 흐른 시간)
  uint32_t rideId;        // 4바이트
  uint8_t  eventLabel;    // 1바이트 (사고 유형 번호 1~5)
};

BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic statusCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLECharacteristic eventCharacteristic("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 13);

// [이벤트 전송 함수] 데이터를 구조체에 담아 라즈베리파이로 무선 송신
void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload;       // 빈 데이터 상자(바구니).
  payload.seq = globalEventSeq++;   // 이벤트 번호를 상자에 넣고, 다음 사고를 위해 번호를 1 올림. (0번, 1번, 2번...)
  payload.timestamp = millis();     // 아두이노가 켜진 후 몇 밀리초(ms)만에 사고가 났는지 시간 정보
  payload.rideId = currentRideId;   // 현재 연결된 주행 세션 ID(예: 1001).
  payload.eventLabel = label;       // 어떤 사고 유형인지 (1:전도, 2:충돌, 3:급가속, 4:급정거, 5:이탈)

  // 세 번째 인자 'true' 설정 -> 라즈베리파이 수신 성공 응답을 기다리는 안전 모드(With Response)
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

unsigned long wearStart = 0;   
bool isWearing = false;        

bool wasCrashTriggered = false; // 충돌 발생 여부 임시 플래그 (라벨 5 트리거용)
unsigned long crashTime = 0;   // 충돌 발생 시점 저장용 타이머

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

  // [Ride ID 제어] 새로운 연결 확정 시마다 세션 번호를 자동 증가시켜 데이터 파편화 방지
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

  // 센서 데이터 갱신 파트
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 좌우 압력이 모두 임계값 이상이고, 불균형 치우침이 없을 때 가착용 상태로 인정
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  // --- [착용 상태 제어 파트] ---
  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis(); // 타이머 시작
    // 가착용 상태가 2초(CONFIRM_MS) 이상 지속되면 완전히 착용한 것(WORN)으로 판정
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusCharacteristic.writeValue(1); // 라즈베리파이에 착용 상태 전송
      Serial.println("[STATUS] 상태 변경 -> 헬멧 착용됨 (WORN)");
    }
  } else {
    wearStart = 0; // 착용 조건 미달 시 타이머 즉시 초기화
    if (isWearing) {
      isWearing = false; 
      statusCharacteristic.writeValue(0); // 라즈베리파이에 미착용 상태 전송
      Serial.println("[STATUS] 상태 변경 -> 헬멧 벗음 (IDLE)");

      // [라벨 5 예외처리] 큰 충돌(라벨 2)이 발생한 직후 3초 이내에 헬멧이 탈착된 경우 트리거
      if (wasCrashTriggered && (millis() - crashTime < 3000)) {
        sendEncodedEvent(5, 0, ax, ay); 
        tone(BUZZER_PIN, 3000, 1000); 
      }
      wasCrashTriggered = false; 
    }
  }

  // --- [사고 감지 파트] ---
  float impact = sqrt(ax*ax + ay*ay + az*az); // 3축 종합 물리 충격량 계산
  
  static unsigned long fallStartTime = 0; 
  static unsigned long lastAccEventTime = 0;   
  static unsigned long lastDecEventTime = 0;   
  
  // 헬멧이 좌우로 기울어지거나(기울기 벡터 1.2G 초과), 완전히 뒤집힌 상태(az < -0.5) 연산
  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  // [안전장치] 미착용(IDLE) 상태라면 하드웨어 움직임이 아무리 격렬해도 사고 판단 전면 스킵
  if (!isWearing) {
    fallStartTime = 0;
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }
  // [라벨 2: 충돌] 순간적인 강한 물리적 충격 가해짐
  else if (impact > CRASH_THR) {
    sendEncodedEvent(2, impact, ax, ay); 
    tone(BUZZER_PIN, 2000, 500); 
    
    wasCrashTriggered = true;  // 라벨 5 판단을 위해 흔적 기록
    crashTime = millis();      // 충돌 발생 시점 저장
    
    fallStartTime = 0;         // 충돌이 우선이므로 전도 타이머는 초기화
  } 
  // [라벨 3: 급가속] 가속도가 기준치 이상 정방향이고, 고개가 비정상적으로 꺾이지 않은 평시 상태일 때만 인정
  else if (ax > SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastAccEventTime > SUDDEN_LOCK_MS) { // 3초 타임아웃 디바운스 적용
      sendEncodedEvent(3, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200); 
      lastAccEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  // [라벨 4: 급정거] 가속도가 역방향(음수)이고, 고개가 수평을 유지하고 있을 때만 인정
  else if (ax < -SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastDecEventTime > SUDDEN_LOCK_MS) { // 3초 타임아웃 디바운스 적용
      sendEncodedEvent(4, impact, ax, ay); 
      tone(BUZZER_PIN, 1500, 200); 
      lastDecEventTime = millis(); 
    }
    fallStartTime = 0; 
  }
  // [라벨 1: 전도] 비정상적인 기울어짐 현상 포착
  else if (isCurrentlyTilted) {
    if (fallStartTime == 0) {
      fallStartTime = millis(); // 기울어지기 시작한 첫 시점 기록
    }
    
    // 단순 고개 숙임이나 일시적 역동적 움직임이 아니라, 기울어진 채로 1.5초 이상 유지되면 사고로 확정
    if (millis() - fallStartTime > 1500) {
      sendEncodedEvent(1, impact, ax, ay); 
      tone(BUZZER_PIN, 1000, 500); 
      fallStartTime = millis(); // 연속 전도 판단을 위한 타이머 갱신
    }
  }
  // 아무 이상 없는 안전 운행 상태일 때 내부 사고 버퍼링 변수 정리
  else {
    fallStartTime = 0;
    // 충돌 흔적이 남은 지 3초가 지나면 무효 처리
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }

  delay(100); // 0.1초 주기로 연산 반복 유도
}