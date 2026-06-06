edge-pi/src/communication

헬멧 유닛(Arduino Nano 33 BLE)과의 블루투스 통신 및 백엔드 서버와의 MQTT 통신을 담당하는 관문(Gateway) 영역이다.

## 1. 개요

- 아두이노가 센서(압력, IMU) 원시 데이터를 1차 연산한 뒤, 바이너리 구조체로 압축 전송
- 멱등성 보장: `rideId + seq` 조합을 중복 판별 키로 사용
- Fail-Safe: BLE 단절 시 즉시 상태 초기화, MQTT status 발행

## 2. BLE 프로토콜 명세

### GATT 서비스

`19B10000-E8F2-537E-4F6C-D104768A1214`

| UUID (suffix) | 방향 | 속성 | 크기 | 설명 |
|:---|:---|:---|:---|:---|
| `...10001...` | Arduino → Pi | Read \| Notify | 1 byte | 헬멧 착용 상태 |
| `...10002...` | Arduino → Pi | Read \| Notify | 14 bytes | 안전 이벤트 구조체 |
| `...10003...` | Pi → Arduino | Write | 1 byte | 제어 명령 |

### Arduino → Pi: 착용 상태 (19B10001)

```
byte[0]: 0x00 = 미착용 (IDLE)
         0x01 = 착용 확정 (WORN, 2초 유지 후)
```

### Arduino → Pi: 안전 이벤트 (19B10002) — 리틀엔디안 바이너리 `<BIIIB`

```
Offset  Type     Name            값
0       uint8    schemaVersion   항상 1
1–4     uint32   seq             이벤트 순번 (rideId 교체 시 0 초기화)
5–8     uint32   timestamp       아두이노 millis() (ms)
9–12    uint32   rideId          BLE 연결마다 +1 증가
13      uint8    eventLabel      0=정상, 1=전도, 2=충돌, 3=급가속, 4=급정거, 5=충돌후이탈
```

총 14 bytes. Pi 파싱: `struct.unpack("<BIIIB", data)`

### Pi → Arduino: 제어 명령 (19B10003)

```
0x01: 후방 접근 경고 — 헬멧 버저 300ms 울리기
```

## 3. MQTT 토픽

| 토픽 | 방향 | 설명 |
|:---|:---|:---|
| `device/{PI_ID}/telemetry` | Pi → Server | 주행 상태 + 안전 판단 결과 |
| `device/{PI_ID}/status`    | Pi → Server | 헬멧 BLE 연결/끊김 이벤트 |
| `device/{PI_ID}/event`     | Pi → Server | 긴급 사고 이벤트 (예비) |
| `device/{PI_ID}/emergency` | Pi → Server | 응급 상황 (예비) |

## 4. 파일 구성

- `comm_config.py`: UUID, 명령 코드, MQTT 토픽/브로커 상수
- `ble_manager.py`: Bleak 기반 BLE 수신/송신, 재연결 루프, 연결 콜백
- `mqtt_client.py`: MQTT 발행 (telemetry, status)
