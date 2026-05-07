#include <ArduinoBLE.h>

// BLE 서비스 및 특성 UUID 설정 (임의 생성 가능)
BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
// 0: UNWORN, 1: WORN, 2: EMERGENCY
BLEByteCharacteristic statusCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

void setup() {
  Serial.begin(9600);
  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Alpha"); // 라즈베리파이가 찾을 장치 이름 [cite: 166]
  BLE.setAdvertisedService(helmetService);
  helmetService.addCharacteristic(statusCharacteristic);
  BLE.addService(helmetService);
  
  statusCharacteristic.writeValue(0); // 초기 상태: 미착용
  BLE.advertise();
  Serial.println("BLE 광고 중...");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    while (central.connected()) {
      // 센서 로직에 따라 값 업데이트 [cite: 99, 103]
      // 예: 압력 센서 감지 시 1(WORN), 사고 감지 시 2(EMERGENCY)
      int currentStatus = checkHelmetStatus(); 
      statusCharacteristic.writeValue(currentStatus);
      delay(200); // 200ms 주기로 데이터 전송 
    }
  }
}

int checkHelmetStatus() {
  // 실제 센서 읽기 로직이 들어갈 자리 [cite: 108, 110]
  return 1; // 테스트용 '착용' 신호
}