const int BUZZER_PIN = 2; // 부저의 + 다리가 연결된 핀

// 음계별 주파수 정의
int melody[] = {262, 294, 330, 349, 392, 440, 494, 523};

void setup() {
  Serial.begin(9600);
  Serial.println("--- 수동 부저 음계 테스트 시작 ---");
}

void loop() {
  for (int i = 0; i < 8; i++) {
    // tone(핀번호, 주파수, 지속시간)
    tone(BUZZER_PIN, melody[i], 250); 
    
    Serial.print("Playing Frequency: ");
    Serial.println(melody[i]);
    
    delay(400); // 음 사이의 간격
  }
  
  noTone(BUZZER_PIN); // 소리 끄기
  delay(2000); // 2초 쉬고 다시 시작
}