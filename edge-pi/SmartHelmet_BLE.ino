#include <ArduinoBLE.h>

const int FSR_PIN = A0; 
const int PRES_THR = 300; 
unsigned long q_count = 0; 

BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
// 64바이트 문자열 특성
BLECharacteristic dataCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify, 64);

void setup() {
  Serial.begin(9600);
  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Alpha");
  BLE.setAdvertisedService(helmetService);
  helmetService.addCharacteristic(dataCharacteristic);
  BLE.addService(helmetService);
  
  BLE.advertise();
  Serial.println("Q:T:W:A:S 패킷 송신 준비 완료");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("연결됨: ");
    Serial.println(central.address());

    while (central.connected()) {
      int isWorn = (analogRead(FSR_PIN) > PRES_THR) ? 1 : 0; 
      int isAccident = 0;                                    
      float currentSpeed = 0.0;                              
      unsigned long timeStamp = millis();                   

      String packet = "Q:" + String(q_count) + 
                      ",T:" + String(timeStamp) + 
                      ",W:" + String(isWorn) + 
                      ",A:" + String(isAccident) + 
                      ",S:" + String(currentSpeed);

      dataCharacteristic.writeValue(packet);
      
      Serial.println("Sent: " + packet);
      q_count++;
      delay(200); 
    }
    Serial.println("연결 끊김");
  }
}