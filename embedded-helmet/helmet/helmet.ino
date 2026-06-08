#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const int FSR_L_PIN  = A0;
const int FSR_R_PIN  = A1;

const int  PRES_THR    = 300;   // FSR 착용 판정 임계값
const int  BAL_TOL     = 150;   // 좌우 압력 불균형 허용치
const long CONFIRM_MS  = 2000;  // 착용 확정 유지 시간

const float CRASH_THR  = 4.0;   // 충돌 감지 임계값 (G)
const float FALL_THR   = 1.2;   // 전도 기울기 임계값 (G)
const float SUDDEN_THR = 0.8;   // 급가속/급정거 임계값 (G)

// 라벨 2(충돌), 3(급가속), 4(급정거) 공통 디바운스
const unsigned long SUDDEN_LOCK_MS    = 3000;
// 전도(라벨 1) 확정까지 기울어짐 유지 필요 시간
const unsigned long FALL_CONFIRM_MS   = 1500;
// [FIX BUG-E] 전도 이벤트 재전송 최소 간격 — 기울어진 채 유지 시 1.5s마다 폭탄 방지
const unsigned long FALL_REPEAT_LOCK_MS = 8000;
// 100ms 주기 센서 처리
const unsigned long LOOP_INTERVAL_MS  = 100;

uint32_t currentRideId  = 1000;
uint32_t globalEventSeq = 0;

// [FIX BUG-1] schemaVersion 첫 필드 추가 → 14 bytes (Pi의 <BIIIB 와 일치)
// 이전: seq(4)+timestamp(4)+rideId(4)+label(1) = 13 bytes → eventLabel 항상 0으로 파싱됨
struct __attribute__((packed)) SafetyEventPayload {
  uint8_t  schemaVersion; // 1  (고정값 1, CLAUDE.md 계약)
  uint32_t seq;           // 4
  uint32_t timestamp;     // 4  (millis, ms)
  uint32_t rideId;        // 4
  uint8_t  eventLabel;    // 1  (1~5)
}; // 총 14 bytes

BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic statusCharacteristic(
  "19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
// [FIX BUG-1] 크기 13 → 14
BLECharacteristic eventCharacteristic(
  "19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 14);
void sendEncodedEvent(uint8_t label, float impactG, float ax, float ay) {
  SafetyEventPayload payload;
  payload.schemaVersion = 1; // [FIX BUG-1]
  payload.seq           = globalEventSeq++;
  payload.timestamp     = millis();
  payload.rideId        = currentRideId;
  payload.eventLabel    = label;

  eventCharacteristic.writeValue((uint8_t*)&payload, sizeof(SafetyEventPayload), true);

  Serial.print("[EVENT] Seq="); Serial.print(payload.seq);
  Serial.print(" RideID=");     Serial.print(payload.rideId);
  Serial.print(" Label=");      Serial.print(label);
  switch (label) {
    case 1: Serial.println(" (전도)");           break;
    case 2: Serial.print(" (충돌) "); Serial.print(impactG); Serial.println("G"); return;
    case 3: Serial.println(" (급가속)");         break;
    case 4: Serial.println(" (급정거)");         break;
    case 5: Serial.println(" (충돌 후 이탈)");   break;
  }
  Serial.print("  ax="); Serial.print(ax);
  Serial.print(" ay=");  Serial.println(ay);
}

unsigned long wearStart         = 0;
bool          isWearing         = false;
bool          wasCrashTriggered = false;
unsigned long crashTime         = 0;
bool          oldCentralConnected = false;
unsigned long lastLoopTime      = 0;

void setup() {
  Serial.begin(9600);
  // [FIX BUG-3] USB 없이 배터리 단독 구동 시 무한 대기 방지 (3초 타임아웃)
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 3000);

  if (!IMU.begin()) {
    Serial.println("[ERR] IMU 초기화 실패");
    while (1);
  }

  if (!BLE.begin()) {
    Serial.println("[ERR] BLE 초기화 실패");
    while (1);
  }

  // [POWER] 광고 간격 100ms(기본) → 200ms: 미연결 상태 라디오 TX 50% 절감
  // 320 * 0.625ms = 200ms. Pi는 10초 스캔 타임아웃 사용하므로 탐지에 문제없음.
  BLE.setAdvertisingInterval(320);

  BLE.setLocalName("SmartHelmet_Alpha");
  BLE.setAdvertisedService(helmetService);
  helmetService.addCharacteristic(statusCharacteristic);
  helmetService.addCharacteristic(eventCharacteristic);
  BLE.addService(helmetService);

  statusCharacteristic.writeValue(0);
  BLE.advertise();

  Serial.println("[SYS] 준비 완료. 광고 시작.");
}

void loop() {
  // [POWER] delay() 대신 BLE.poll(): BLE 이벤트 처리하면서 nRF52840 sleep 허용
  // delay()는 CPU를 busy-wait 상태로 유지; BLE.poll(ms)는 이벤트 없을 때 WFE로 대기
  BLE.poll(LOOP_INTERVAL_MS);

  // millis 기반 100ms 주기 제어 (BLE.poll이 일찍 리턴할 때 과도한 센서 처리 방지)
  unsigned long now = millis();
  if (now - lastLoopTime < LOOP_INTERVAL_MS) return;
  lastLoopTime = now;

  // ── 연결 상태 변화 감지 ──────────────────────────────────────────────────
  BLEDevice central           = BLE.central();
  bool      currentCentralConnected = central && central.connected();

  if (currentCentralConnected != oldCentralConnected) {
    if (currentCentralConnected) {
      currentRideId++;
      globalEventSeq = 0; // 새 세션마다 seq 초기화 (멱등성 키: rideId+seq)
      Serial.print("[BLE] 연결. 주소="); Serial.println(central.address());
      Serial.print("[BLE] Ride ID=");    Serial.println(currentRideId);

      // 재연결 시 현재 착용 상태 즉시 전송 (Pi가 notify로만 구독하여 초기값 누락 방지)
      statusCharacteristic.writeValue(isWearing ? 1 : 0);
    } else {
      Serial.println("[BLE] 연결 끊김.");
    }
    oldCentralConnected = currentCentralConnected;
  }

  // ── 센서 읽기 ────────────────────────────────────────────────────────────
  int   fsrL = analogRead(FSR_L_PIN);
  int   fsrR = analogRead(FSR_R_PIN);
  float ax = 0, ay = 0, az = 0;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // ── 착용 상태 판정 ───────────────────────────────────────────────────────
  bool isPressed  = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = now;
    if (now - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true;
      statusCharacteristic.writeValue(1);
      Serial.println("[STATUS] 착용됨 (WORN)");
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false;
      statusCharacteristic.writeValue(0);
      Serial.println("[STATUS] 벗음 (IDLE)");

      // 라벨 5: 충돌 후 3초 이내 헬멧 탈착 감지
      if (wasCrashTriggered && (now - crashTime < 3000)) {
        sendEncodedEvent(5, 0, ax, ay);
      }
      wasCrashTriggered = false;
    }
  }

  // ── 사고 감지 ────────────────────────────────────────────────────────────
  float impact = sqrt(ax * ax + ay * ay + az * az);

  static unsigned long fallStartTime      = 0;
  static unsigned long lastFallEventTime  = 0; // [FIX BUG-E]
  static unsigned long lastAccEventTime   = 0;
  static unsigned long lastDecEventTime   = 0;
  static unsigned long lastCrashEventTime = 0; // [FIX BUG-2]

  bool isCurrentlyTilted = (abs(ax) > FALL_THR || abs(ay) > FALL_THR || az < -0.5);

  if (!isWearing) {
    // 미착용 시 사고 감지 전면 차단, 잔여 플래그 정리
    fallStartTime = 0;
    if (wasCrashTriggered && now - crashTime > 3000) wasCrashTriggered = false;
  }
  // 라벨 2: 충돌
  else if (impact > CRASH_THR) {
    // [FIX BUG-2] 디바운스 추가 — 원본에는 없어 충돌 지속 중 100ms마다 이벤트 폭탄 발생
    if (now - lastCrashEventTime > SUDDEN_LOCK_MS) {
      sendEncodedEvent(2, impact, ax, ay);
      lastCrashEventTime = now;
      wasCrashTriggered  = true;
      crashTime          = now;
      fallStartTime      = 0;
    }
  }
  // 라벨 3: 급가속 (az > 0.7 = 헬멧 직립 확인, 원본의 abs(az) 제거 — 뒤집혔을 때 오감지 방지)
  else if (ax > SUDDEN_THR && az > 0.7) {
    if (now - lastAccEventTime > SUDDEN_LOCK_MS) {
      sendEncodedEvent(3, impact, ax, ay);
      lastAccEventTime = now;
    }
    fallStartTime = 0;
  }
  // 라벨 4: 급정거
  else if (ax < -SUDDEN_THR && az > 0.7) {
    if (now - lastDecEventTime > SUDDEN_LOCK_MS) {
      sendEncodedEvent(4, impact, ax, ay);
      lastDecEventTime = now;
    }
    fallStartTime = 0;
  }
  // 라벨 1: 전도 (1.5초 지속 확인 후 전송, 8초 재전송 락아웃)
  // [FIX BUG-E] 기울어진 채 유지 시 1.5s마다 이벤트 폭탄 → FALL_REPEAT_LOCK_MS(8s) 간격으로 제한
  else if (isCurrentlyTilted) {
    if (fallStartTime == 0) fallStartTime = now;
    if (now - fallStartTime > FALL_CONFIRM_MS && now - lastFallEventTime > FALL_REPEAT_LOCK_MS) {
      sendEncodedEvent(1, impact, ax, ay);
      lastFallEventTime = now;
      fallStartTime     = now;
    }
  }
  else {
    fallStartTime = 0;
    if (wasCrashTriggered && now - crashTime > 3000) wasCrashTriggered = false;
  }
}
