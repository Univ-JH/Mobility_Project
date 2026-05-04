const int FSR_PIN = A0; // FSR 센서가 연결된 아날로그 핀

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("--- FSR 압력 센서 테스트 시작 ---");
}

void loop() {
  // 아날로그 값 읽기 (0 ~ 1023)
  int fsrValue = analogRead(FSR_PIN);

  // 전압으로 변환 (나노 33 BLE는 3.3V 기준)
  float voltage = fsrValue * (3.3 / 1023.0);

  Serial.print("Raw Value: ");
  Serial.print(fsrValue);
  Serial.print("\t Voltage: ");
  Serial.print(voltage);
  Serial.print("V\t 상태: ");

  // 힘의 정도를 간단히 분류
  if (fsrValue < 10) {
    Serial.println("누름 없음");
  } else if (fsrValue < 200) {
    Serial.println("살짝 눌림");
  } else if (fsrValue < 500) {
    Serial.println("보통 압력");
  } else if (fsrValue < 800) {
    Serial.println("강하게 눌림");
  } else {
    Serial.println("매우 강한 압력!");
  }

  delay(200);
}