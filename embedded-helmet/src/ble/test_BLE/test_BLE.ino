#include <ArduinoBLE.h>

// 고유 ID (이건 건드리지 마세요)
BLEService customService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEIntCharacteristic customChar("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패!");
    while (1);
  }

  // ★ 중요: 여기서 나온 주소를 메모장에 적어두세요! ★
  String address = BLE.address();
  Serial.println("===============================");
  Serial.print("아두이노 맥 주소: "); 
  Serial.println(address); 
  Serial.println("===============================");

  BLE.setLocalName("MyArduino");
  BLE.setAdvertisedService(customService);
  customService.addCharacteristic(customChar);
  BLE.addService(customService);
  customChar.writeValue(0);
  BLE.advertise();
}

void loop() {
  static int val = 0;
  customChar.writeValue(val++); // 0, 1, 2... 계속 보냄
  Serial.print("Data Sent: "); Serial.println(val);
  delay(1000);
}