#include <ArduinoBLE.h>

// 1. 센서 설정
const int FSR_PIN = A0;       // 센서 신호(S) 연결 핀
const int PRES_THR = 300;     // 착용 판단 임계값 (0~1023 사이, 테스트 후 조정)

// BLE 서비스 및 특성 설정
BLEService helmetService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic statusCharacteristic("19B10001-E8F2-537E-4F6C-D104768A1214", BLERead | BLENotify);

void setup() {
  Serial.begin(9600);
  //while (!Serial); // PC 연결 없이 단독 실행 시 주석 처리 가능

  if (!BLE.begin()) {
    Serial.println("BLE 시작 실패!");
    while (1);
  }

  BLE.setLocalName("SmartHelmet_Alpha");
  BLE.setAdvertisedService(helmetService);
  helmetService.addCharacteristic(statusCharacteristic);
  BLE.addService(helmetService);
  
  statusCharacteristic.writeValue(0); 
  BLE.advertise();
  Serial.println("센서 데이터 전송 준비 완료!");
}

void loop() {
  BLEDevice central = BLE.central();
  if (central) {
    Serial.print("연결됨: ");
    Serial.println(central.address());

    while (central.connected()) {
      // 2. 센서 상태 확인 및 BLE 전송
      int currentStatus = checkHelmetStatus(); 
      statusCharacteristic.writeValue(currentStatus);

      // 시리얼 모니터로 현재 값 모니터링 (디버깅용)
      Serial.print("현재 상태: ");
      Serial.println(currentStatus == 1 ? "착용 중 (1)" : "미착용 (0)");

      delay(200); // 0.2초마다 업데이트
    }
    Serial.println("연결 끊김");
  }
}

// 3. 실제 센서 읽기 함수
int checkHelmetStatus() {
  int fsrValue = analogRead(FSR_PIN); // A0 핀 읽기
  
  // 기준치(300)보다 많이 눌리면 착용(1), 아니면 미착용(0) 반환
  if (fsrValue > PRES_THR) {
    return 1; 
  } else {
    return 0;
  }
}