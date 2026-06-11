#!/bin/bash
# 수동 녹화 제어 스크립트 (main.py 독립형 버전)

RECORDING_DIR="/tmp/recordings"
PID_FILE="/tmp/camera_record.pid"

case "$1" in
  start)
    # 1. 저장 폴더가 없으면 자동으로 생성
    mkdir -p "$RECORDING_DIR"

    # 2. 이미 녹화가 돌고 있는지 확인
    if [ -f "$PID_FILE" ]; then
      echo "⚠️ 이미 녹화가 진행 중입니다. (PID: $(cat $PID_FILE))"
      exit 1
    fi

    # 3. 라즈베리 파이 카메라를 깨워 백그라운드에서 진짜 녹화 시작
    # --inline 설정을 넣어 파일 손상을 방지하고, 현재 날짜시간으로 저장합니다.
    FILE_NAME="manual_$(date +%Y%m%d_%H%M%S).h264"
    libcamera-vid -t 0 --inline -o "$RECORDING_DIR/$FILE_NAME" > /dev/null 2>&1 &
    
    # 4. 방금 켠 카메라 프로세스의 번호(PID)를 서랍에 저장
    echo $! > "$PID_FILE"
    echo "🎥 블랙박스 수동 녹화 시작 완료!"
    echo "💾 저장 위치: $RECORDING_DIR/$FILE_NAME"
    ;;

  stop)
    # 1. 녹화 중인 프로세스가 있는지 확인
    if [ ! -f "$PID_FILE" ]; then
      echo "⚠️ 현재 녹화 중이 아닙니다."
      exit 1
    fi

    # 2. 저장해둔 번호를 찾아 카메라 프로세스를 안전하게 종료 (영상 저장)
    TARGET_PID=$(cat "$PID_FILE")
    kill "$TARGET_PID" 2>/dev/null
    rm -f "$PID_FILE"
    echo "💾 영상 파일 빌드 완료 및 카메라 안전 종료!"
    ;;

  status)
    if [ -f "$PID_FILE" ]; then
      echo "🔴 녹화 중입니다. (카메라 프로세스 번호: $(cat $PID_FILE))"
    else
      echo "🌑 현재 녹화가 중지된 상태입니다."
    fi
    ;;

  list)
    echo "저장된 영상 목록 ($RECORDING_DIR):"
    ls -lh "$RECORDING_DIR"/*.h264 2>/dev/null || echo "   (저장된 영상 없음)"
    ;;

  *)
    echo "사용법: $0 {start|stop|status|list}"
    exit 1
    ;;
esac