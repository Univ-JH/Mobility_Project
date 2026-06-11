#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

/* ===========================================================
   [1. 하드웨어 설정 및 사고 판단 기준값]
   =========================================================== */
const int FSR_PIN = A0;        // 단일 압력 센서 꼽는 핀 (A0로 통합)

const int PRES_THR = 300;      // 착용 판정 기준 (센서 값이 300보다 커야 함)
const long CONFIRM_MS = 1000;  // 착용 확인 대기시간 (1초 동안 쓰고 있어야 "착용 완료")
const long DETACH_MS = 3000;   // 벗음 확인 대기시간 (3초 동안 벗고 있어야 "벗음 완료")

const float CRASH_THR = 4.0;   // 충돌 감지 기준 (4.0G 이상의 강한 물리적 충격)
const float FALL_THR = 1.2;    // 전도(넘어짐) 감지 기준 (좌우 기울기 변화량)
const float SUDDEN_THR = 0.8;  // 급가속 및 급정거 판단 기준값

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
// 14바이트 데이터를 가로채 갈 수 있도록 크기를 정확히 14로 세팅
BLECharacteristic eventCharacteristic("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);

// [데이터 포장 및 전송 함수] 사고가 났을 때 라즈베리파이로 무선 신호를 쏘는 핵심 기능
void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload; // 데이터 상자 하나 열기
  
  // 상자에 데이터 차곡차곡 채워 넣기
  payload.schemaVersion = SCHEMA_VERSION;
  payload.seq = globalEventSeq++;
  payload.timestamp = millis(); // 아두이노 타이머 기준 현재 시간 입력
  payload.rideId = currentRideId; 
  payload.eventLabel = label;

  // 세 번째 인자를 true로 설정: 라즈베리파이가 "잘 받았다"고 응답할 때까지 기다리는 안전 모드
  eventCharacteristic.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload), true);
  
  // 컴퓨터 화면(시리얼 모니터)에 테스트용 로그 출력
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
   [3. 초기 설정 (보드가 처음 켜질 때 1번만 실행)]
   =========================================================== */
unsigned long wearStart = 0;   // 헬멧 쓰기 시작한 시간 측정용 변수
unsigned long detachStart = 0; // 헬멧을 벗기 시작한(센서가 떨어진) 시간 측정용 변수
bool isWearing = false;        // 현재 헬멧을 쓰고 있는지 저장하는 상태 변수

bool wasCrashTriggered = false; // 충돌이 났었는지 기억하는 플래그 (라벨 5용)
unsigned long crashTime = 0;    // 충돌이 발생했던 시점 기록용 타이머

bool oldCentralConnected = false; // 직전 블루투스 연결 상태 기억용

void setup() {
  Serial.begin(9600);
//   while (!Serial); // 배터리 구동을 위해 무한 대기 코드는 주석 처리 제거 상태 유지

  // 센서 장치들이 제대로 켜졌는지 확인 (안 켜지면 여기서 프로그램이 멈춤)
  if (!IMU.begin()) {
    Serial.println("오류: IMU(가속도 센서) 초기화 실패!");
    while (1);
  }
  if (!BLE.begin()) {
    Serial.println("오류: BLE(블루투스 모듈) 초기화 실패!");
    while (1);
  }

  // 블루투스 이름 및 서비스 등록 과정
  BLE.setLocalName("SmartHelmet_Alpha");
  BLE.setAdvertisedService(helmetService);
  
  helmetService.addCharacteristic(statusCharacteristic);
  helmetService.addCharacteristic(eventCharacteristic);
  BLE.addService(helmetService);
  
  statusCharacteristic.writeValue(0); // 처음엔 미착용(0) 상태로 초기값 세팅
  BLE.advertise(); // 스마트폰이나 라즈베리파이가 검색할 수 있도록 신호 방출 시작

  Serial.println("시스템 준비 완료");
}

/* ===========================================================
   [4. 메인 루프 (아두이노가 켜져 있는 동안 무한 반복 구동)]
   =========================================================== */
void loop() {
  // 블루투스 중앙 장치(라즈베리파이 등)가 연결되었는지 상시 체크
  BLEDevice central = BLE.central();
  bool currentCentralConnected = central && central.connected();

  // 블루투스 연결이 새로 되거나 끊겼을 때 감지하는 로직
  if (currentCentralConnected != oldCentralConnected) {
    if (currentCentralConnected) {
      currentRideId++; // 새로 연결될 때마다 주행 세션 ID를 1씩 증가시킴
      
      Serial.print("\n[BLE] 중앙 장치와 연결되었습니다. 기기 주소: ");
      Serial.println(central.address());
      Serial.print("[BLE] 발급된 새로운 Ride ID: ");
      Serial.println(currentRideId);
    } else {
      Serial.println("\n[BLE] 중앙 장치와의 연결이 끊어졌습니다.");
    }
    oldCentralConnected = currentCentralConnected; // 상태 동기화
  }

  // 압력 센서(1개) 및 가속도(IMU) 센서 데이터 실시간 읽어오기
  int fsrValue = analogRead(FSR_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 단 하나의 압력 센서만 임계값(PRES_THR)을 넘으면 착용한 것으로 판별
  bool isPressed = (fsrValue > PRES_THR);

  // --- [착용 상태 제어 파트 - 3초 타이머 고도화] ---
  if (isPressed) {
    detachStart = 0; // 다시 센서가 눌렸으므로 벗음 타이머는 리셋
    
    if (wearStart == 0) wearStart = millis(); // 머리가 닿은 순간 착용 타이머 가동
    
    // 1초(CONFIRM_MS) 이상 계속 머리가 닿아있고, 아직 미착용 상태라면 최종 착용으로 인정
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true; 
      statusCharacteristic.writeValue(1); // 라즈베리파이에 "헬멧 썼음(1)" 신호 전달
      Serial.println("[STATUS] 상태 변경 -> 헬멧 착용됨 (WORN)");
    }
  } 
  else {
    wearStart = 0; // 센서가 떨어졌으므로 착용 타이머는 리셋
    
    if (isWearing) {
      // 센서가 떨어진 최초의 순간을 기록 (벗음 타이머 작동 시작)
      if (detachStart == 0) detachStart = millis(); 
      
      // 센서에서 힘이 빠진 상태가 연속으로 3초(DETACH_MS)를 넘어야 최종 '벗음' 판단
      if (millis() - detachStart > DETACH_MS) {
        isWearing = false; 
        detachStart = 0; // 상태가 바뀌었으므로 타이머 리셋
        statusCharacteristic.writeValue(0); // 라즈베리파이에 "헬멧 벗었음(0)" 신호 전달
        Serial.println("[STATUS] 상태 변경 -> 헬멧 벗음 (IDLE)");

        // [라벨 5 처리]: 착용 중 대형 충돌(라벨 2)이 난 뒤 3초 이내에 헬멧을 벗어 던진 상황 처리
        if (wasCrashTriggered && (millis() - crashTime < 3000)) {
          sendEncodedEvent(5, 0, ax, ay); // 라벨 5번 이벤트 즉시 전송
        }
        wasCrashTriggered = false; 
      }
    } else {
      detachStart = 0; // 이미 벗겨진 상태라면 타이머 리셋 유지
    }
  }

  // --- [사고 감지 파트] ---
  float impact = sqrt(ax*ax + ay*ay + az*az); // 3축 가속도를 하나로 뭉친 종합 충격량 공식
  
  static unsigned long fallStartTime = 0;    // 전도(기울어짐) 지속시간 측정 타이머
  static unsigned long lastSuddenEventTime = 0; // 급가속과 급정거 오작동 및 엉킴을 막기 위한 통합 제어 타이머
  
  // 헬멧이 좌우로 과하게 꺾이거나, 완전히 거꾸로 뒤집힌(az < -0.5) 상태 연산
  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  // 미착용 상태일 때는 모든 사고 연산을 전면 스킵하고 초기화 시킴
  if (!isWearing) {
    fallStartTime = 0;
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }
  // 착용 중이며, 큰 충격이 온 경우 (충돌 라벨 2)
  else if (impact > CRASH_THR) {
    sendEncodedEvent(2, impact, ax, ay); // 충돌 패킷 전송
    
    wasCrashTriggered = true; // 라벨 5번 트리거를 위해 기록을 남겨둠
    crashTime = millis();     // 충돌 난 시간 박제
    
    fallStartTime = 0; // 충돌이 우선이므로 전도 타이머는 리셋
  } 
  // 고개를 숙인 게 아니고 수평을 유지하면서 앞방향으로 급가속 한 경우 (라벨 3)
  else if (ax > SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastSuddenEventTime > SUDDEN_LOCK_MS) { // 전송 규격 제한 시간이 만료되었을 때만 전송
      sendEncodedEvent(3, impact, ax, ay); 
      lastSuddenEventTime = millis(); // 마지막 기동 시간 박제하여 급정거 간섭 차단
    }
    fallStartTime = 0; 
  }
  // 고개를 숙인 게 아니고 수평을 유지하면서 뒷방향으로 급브레이크 밟은 경우 (라벨 4)
  else if (ax < -SUDDEN_THR && abs(az) > 0.7) {
    if (millis() - lastSuddenEventTime > SUDDEN_LOCK_MS) { // 전송 규격 제한 시간이 만료되었을 때만 전송
      sendEncodedEvent(4, impact, ax, ay); 
      lastSuddenEventTime = millis(); // 마지막 기동 시간 박제하여 급가속 간섭 차단
    }
    fallStartTime = 0; 
  }
  // [착용 중일 때만] 위 조건들을 다 빗겨나갔는데 헬멧이 자빠져 누워있는 경우 (전도 라벨 1)
  else if (isCurrentlyTilted) {
    if (fallStartTime == 0) {
      fallStartTime = millis(); // 기울어지기 시작한 최초의 시점 기록
    }
    
    // 단순 움직임이 아니라, 1.5초 연속으로 누워있음이 유지될 때 비로소 "전도 사고"로 최종 확정
    if (millis() - fallStartTime > 1500) {
      sendEncodedEvent(1, impact, ax, ay); // 전도 패킷 전송
      fallStartTime = millis(); // 연속 전도 판단을 위해 타이머 리셋
    }
  }
  // 아무 사고도 없고 정상적으로 똑바로 서서 달리는 평화로운 상태일 때 변수 정리
  else {
    fallStartTime = 0; // 전도 타이머 리셋
    // 충돌 흔적이 남은 지 3초가 지나가면 흔적을 지워줌
    if (wasCrashTriggered && (millis() - crashTime > 3000)) {
      wasCrashTriggered = false;
    }
  }

  delay(100); // 0.1초마다 센서 감지 루프를 반복 구동
}