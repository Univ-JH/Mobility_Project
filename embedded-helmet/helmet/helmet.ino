#include <ArduinoBLE.h>
#include <Arduino_LSM9DS1.h>

const int BUZZER_PIN = 2;      // 부저

// 1. 착용 감지 (압력 센서) 관련
const int FSR_L_PIN = A0;      // 왼쪽 센서 핀
const int FSR_R_PIN = A1;      // 오른쪽 센서 핀
const int PRES_THR = 300;      // 착용 판단 압력 임계값
const int BAL_TOL = 150;       // 좌우 균형 허용 오차
const long CONFIRM_MS = 2000;  // 착용 확정 대기 시간 (2초)

// 2. 사고 감지 (IMU 센서) 관련
const float CRASH_THR = 4.0;   // 충돌 사고 감지 중력 가속도 값
const float FALL_THR = 0.8;    // 전도(쓰러짐) 감지 기울기 값
const float SUDDEN_THR = 1.5;  // 급가속/급정거 감지 임계값

// 3. BLE 서비스 관련
const char* SVC_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214";
const char* ST_UUID  = "19B10001-E8F2-537E-4F6C-D104768A1214"; // 상태(착용여부)
const char* EV_UUID  = "19B10002-E8F2-537E-4F6C-D104768A1214"; // 이벤트(사고)

BLEService helmetSvc(SVC_UUID);
BLEByteCharacteristic statusChar(ST_UUID, BLERead | BLENotify);
BLEByteCharacteristic eventChar(EV_UUID, BLERead | BLENotify);

unsigned long wearStart = 0;   // 처음 눌린 시간 저장
bool isWearing = false;        // 현재 착용 상태 여부

void setup() {
  Serial.begin(9600);

  pinMode(BUZZER_PIN, OUTPUT); // 부저 출력 설정

  // IMU와 BLE 초기화 (둘 중 하나라도 실패 시 중단)
  if (!IMU.begin() || !BLE.begin()) {
    Serial.println("센서 또는 BLE 초기화 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet");
  BLE.setAdvertisedService(helmetSvc);
  
  // 특성(Characteristic) 추가
  helmetSvc.addCharacteristic(statusChar);
  helmetSvc.addCharacteristic(eventChar);
  
  BLE.addService(helmetSvc);
  
  // 초기값 설정
  statusChar.writeValue(0);
  eventChar.writeValue(0);
  
  BLE.advertise();
  Serial.println("헬멧 시스템 시작...");
}

void loop() {
  BLEDevice central = BLE.central();

  // 1. 센서값 읽기 (압력 및 가속도)
  int fsrL = analogRead(FSR_L_PIN);
  int fsrR = analogRead(FSR_R_PIN);
  

  //가속도 ax: 헬멧이 앞뒤로 흔들리는 정도,ay: 헬멧이 옆으로 흔들리는 정도,az: 헬멧이 위아래로 흔들리는 정도
  float ax, ay, az;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);
  }

  // 2. 착용 판별 (히스테리시스 로직)
  bool isPressed = (fsrL > PRES_THR) && (fsrR > PRES_THR); // 양쪽 다 눌림
  bool isBalanced = abs(fsrL - fsrR) < BAL_TOL;            // 좌우 균형 맞음

  if (isPressed && isBalanced) {
    if (wearStart == 0) wearStart = millis(); // 처음 눌린 시점 기록
    
    // 설정한 시간(2초) 동안 유지되었다면 착용으로 판정
    if (millis() - wearStart > CONFIRM_MS && !isWearing) {
      isWearing = true;
      statusChar.writeValue(1);
      Serial.println("상태: 착용 완료");
    }
  } else {
    wearStart = 0; // 조건 안 맞으면 시간 초기화
    if (isWearing) {
      isWearing = false;
      statusChar.writeValue(0);
      Serial.println("상태: 미착용");
    }
  }

  // 3. 사고 감지 로직
  // 충격량(벡터 합) 계산
  float impact = sqrt(ax*ax + ay*ay + az*az);
  
  if (impact > CRASH_THR) {
    eventChar.writeValue(2); // 2: 충돌(Crash)
    Serial.println("이벤트: 충돌 발생!");
    tone(BUZZER_PIN, 2000, 500); // 부저 울림
  } 
  else if (ax > SUDDEN_THR) {
    eventChar.writeValue(3); // 3: 급가속
    Serial.println("이벤트: 급가속 발생!");
    tone(BUZZER_PIN, 1500, 200); 
  }
  else if (ax < -SUDDEN_THR) {
    eventChar.writeValue(4); // 4: 급정거
    Serial.println("이벤트: 급정거 발생!");
    tone(BUZZER_PIN, 1500, 200);
  }
  //얼마나 옆으로 기울어졌나 확인
  else if (abs(ax) > FALL_THR && isWearing) {
    eventChar.writeValue(1); // 1: 전도(Fall)
    Serial.println("이벤트: 전도 발생!");
    tone(BUZZER_PIN, 1000, 500); // 부저 울림
  }

  delay(1000); // 1초마다 반복
}