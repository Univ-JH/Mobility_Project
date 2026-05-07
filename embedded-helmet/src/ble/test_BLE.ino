#include <ArduinoBLE.h>

BLEService testService("19B10000-E8F2-537E-4F6C-D104768A1214"); // 서비스 UUID
BLEIntCharacteristic testChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Test");
  BLE.setAdvertisedService(testService);
  testService.addCharacteristic(testChar);
  BLE.addService(testService);

  testChar.writeValue(0);
  BLE.advertise();

  Serial.println("블루투스 대기 중... 이름: SmartHelmet_Test");
}

void loop() {
  static int counter = 0;
  testChar.writeValue(counter++); // 0부터 숫자를 계속 올림
  Serial.print("보내는 중: "); Serial.println(counter);
  delay(1000);
}