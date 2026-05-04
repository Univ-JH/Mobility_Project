#include <Arduino_LSM9DS1.h>

void setup() {
  Serial.begin(9600);
  while (!Serial); 

  Serial.println("--- LSM9DS1 상세 가속도 및 기울기 테스트 ---");

  if (!IMU.begin()) {
    Serial.println("IMU 초기화 실패!");
    while (1);
  }

  // 헤더 출력 (구분하기 쉽게 변경)
  Serial.println("ax(G)\tay(G)\taz(G)\t|  Total(G)  |  Roll\tPitch");
}

void loop() {
  float ax, ay, az;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(ax, ay, az);

    // 1. 전체 가속도 합산(Total G) 계산
    // $Total G = \sqrt{ax^2 + ay^2 + az^2}$
    float totalG = sqrt(ax * ax + ay * ay + az * az);

    // 2. 기울기(Angle) 계산
    float roll = atan2(ay, az) * 180.0 / PI;
    float pitch = atan2(-ax, sqrt(ay * ay + az * az)) * 180.0 / PI;

    // 3. 데이터 출력 (G 단위를 강조)
    Serial.print(ax, 2); Serial.print("\t");
    Serial.print(ay, 2); Serial.print("\t");
    Serial.print(az, 2); Serial.print("\t|  ");
    
    Serial.print(totalG, 2); Serial.print(" G  |  "); // 전체 충격량 표시

    Serial.print(roll, 1); Serial.print("\t");
    Serial.println(pitch, 1);
  }

  delay(200); 
}