#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const int BUZZER_PIN = 2;

// 압력 및 사고 임계값 (기존 유지)
const int FSR_L_PIN = A0;
const int FSR_R_PIN = A1;
const int PRES_THR = 300;
const int BAL_TOL = 150;
const long CONFIRM_MS = 2000;
const float CRASH_THR = 4.0;
const float FALL_THR = 0.8;
const float SUDDEN_THR = 1.5;

//서비스 및 특성 정의
BLEService helmetSvc("19B10000-E8F2-537E-4F6C-D104768A1214"); 
// 착용 상태와 사고 이벤트를 각각의 특성으로 정의
BLEIntCharacteristic statusChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);
BLEIntCharacteristic eventChar("19B10002-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

unsigned long wearStart = 0;
bool isWearing = false;

void setup() {
  Serial.begin(9600);
  // while (!Serial); 

  pinMode(BUZZER_PIN, OUTPUT);

  if (!IMU.begin() || !BLE.begin()) {
    Serial.println("초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet");
  BLE.setAdvertisedService(helmetSvc);
  
  helmetSvc.addCharacteristic(statusChar);
  helmetSvc.addCharacteristic(eventChar);
  
  BLE.addService(helmetSvc);
  
  statusChar.writeValue(0);
  eventChar.writeValue(0);
  
  BLE.advertise();
  Serial.println("헬멧 시스템 시작... SmartHelmet 대기 중");
}

void loop() {
  // BLE 연결 상태 확인 (선택 사항)
  BLEDevice central = BLE.central();

  // 센서 데이터 읽기
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 착용 판별 로직
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR);
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;

  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis();
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true;
      statusChar.writeValue(1);
      Serial.println("상태: 착용 완료 (1)");
    }
  } else {
    wearStart = 0;
    if (isWearing) {
      isWearing = false;
      statusChar.writeValue(0);
      Serial.println("상태: 미착용 (0)");
    }
  }

  // 사고 감지 로직 및 BLE 전송
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  if (impact > CRASH_THR) {
    eventChar.writeValue(2); // 충돌
    Serial.println("이벤트: 충돌 (2)");
    tone(BUZZER_PIN, 2000, 500);
  } 
  else if (ax > SUDDEN_THR) {
    eventChar.writeValue(3); // 급가속
    Serial.println("이벤트: 급가속 (3)");
    tone(BUZZER_PIN, 1500, 200);
  }
  else if (ax < -SUDDEN_THR) {
    eventChar.writeValue(4); // 급정거
    Serial.println("이벤트: 급정거 (4)");
    tone(BUZZER_PIN, 1500, 200);
  }
  else if (abs(ax) > FALL_THR && isWearing) {
    eventChar.writeValue(1); // 전도
    Serial.println("이벤트: 전도 (1)");
    tone(BUZZER_PIN, 1000, 500);
  }
  else {
    // 특별한 이벤트가 없으면 0을 유지 (라즈베리파이 확인용)
    if (eventChar.value() != 0) eventChar.writeValue(0);
  }

  delay(100); // 실제 사고 감지를 위해 1초보다는 조금 더 빠르게 조정 (0.1초)
}