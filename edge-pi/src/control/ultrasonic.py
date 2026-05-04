import time
import RPi.GPIO as GPIO
from typing import Union
from .control_config import (
    ULTRASONIC_TRIG, ULTRASONIC_ECHO,
    SOUND_SPEED, TIMEOUT_LIMIT,
    DISTANCE_MIN_THRESHOLD, DISTANCE_MAX_THRESHOLD
)

class UltrasonicSensor:
    def __init__(self):
        """초음파 센서 하드웨어 초기화 (BCM 핀 모드)"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)  # 불필요한 GPIO 경고 메시지 숨김

        GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)
        GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)

        # 센서 초기 상태를 안정적인 LOW로 설정
        GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)
        time.sleep(0.5)  # 센서 안정화 대기

    def get_distance(self, ride_id: str = "N/A") -> float:
        """
        초음파를 발사하여 거리를 측정하고 cm 단위로 반환
        
        Returns:
            float: 측정된 거리(cm). 비정상 감지 시 float('inf') 반환
        """
        try:
            # 1. 초음파 트리거 펄스 생성 (10us 동안 HIGH 유지)
            GPIO.output(ULTRASONIC_TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(ULTRASONIC_TRIG, GPIO.LOW)

            start_time = time.time()
            stop_time = time.time()
            timeout_start = time.time()

            # 2. Echo 핀이 HIGH가 될 때까지 대기 (초음파 발사 시점 측정)
            while GPIO.input(ULTRASONIC_ECHO) == 0:
                start_time = time.time()
                if start_time - timeout_start > TIMEOUT_LIMIT:
                    return self._handle_error("ECHO_START_TIMEOUT", ride_id)

            # 3. Echo 핀이 LOW가 될 때까지 대기 (반사파 수신 시점 측정)
            while GPIO.input(ULTRASONIC_ECHO) == 1:
                stop_time = time.time()
                if stop_time - start_time > TIMEOUT_LIMIT:
                    return self._handle_error("ECHO_STOP_TIMEOUT", ride_id)

            # 4. 소요 시간 기반 거리 계산 (왕복이므로 2로 나눔)
            duration = stop_time - start_time
            distance = (duration * SOUND_SPEED) / 2

            # 5. 유효 거리 필터링 (노이즈 제거)
            if not (DISTANCE_MIN_THRESHOLD <= distance <= DISTANCE_MAX_THRESHOLD):
                # 유효 범위를 벗어난 값은 물리적 노이즈로 간주
                return float('inf')

            return round(distance, 2)

        except Exception as e:
            # 에러 처리: 예외를 삼키지 않고 로그 기록 후 안전 모드 값 반환
            return self._handle_error(f"SENSOR_EXCEPTION_{str(e)}", ride_id)

    def _handle_error(self, reason: str, ride_id: str) -> float:
        """
        구조화 로그 기록 및 보수적 값 반환
        센서 이상 상황 발생 시 호출되어 로그를 남기고 무한대(inf) 거리를 반환
        """
        # 로그 필수 키 (eventType, rideId, severity, reason, confidence) 준수
        log_payload = {
            "eventType": "SENSOR_ANOMALY",
            "rideId": ride_id,
            "severity": "WARNING",
            "reason": reason,
            "confidence": 1.0  # 에러 발생 자체에 대한 확신도는 100%
        }
        
        # 실제 환경에서는 logger.warning(log_payload) 호출 / 하드웨어 테스트 후 서버 전송으로 변경
        print(f"[JSON_LOG] {log_payload}") 
        
        # Fail-Safe: 센서 고장 시 거리를 '0'으로 주면 시스템이 항상 충돌로 오인하여 급제동을 걸 수 있으므로, 
        # 보수적인 값인 'inf(무한대)'를 주어 초음파 센서 판정을 무효화하고 메인 AI 카메라에 의존
        return float('inf')

    def cleanup(self):
        """프로그램 종료 시 GPIO 리소스 안전하게 해제"""
        GPIO.cleanup((ULTRASONIC_TRIG, ULTRASONIC_ECHO))