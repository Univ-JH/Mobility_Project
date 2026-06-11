#!/bin/bash
# 수동 녹화 제어 스크립트
# 사용법:
#   ./record.sh start   — 녹화 시작
#   ./record.sh stop    — 녹화 중지
#   ./record.sh status  — 녹화 중 여부 확인
#   ./record.sh list    — 저장된 영상 목록

RECORDING_DIR="/tmp/recordings"

case "$1" in
  start)
    touch /tmp/record_start
    echo "녹화 시작 신호 전송 완료 (약 0.1초 후 반영)"
    ;;
  stop)
    touch /tmp/record_stop
    echo "녹화 중지 신호 전송 완료"
    ;;
  status)
    if [ -f /tmp/record_start ]; then
      echo "대기 중: 녹화 시작 신호 처리 전"
    else
      echo "메인 프로세스 상태 확인: ps aux | grep main.py"
    fi
    ;;
  list)
    echo "저장된 영상 목록 ($RECORDING_DIR):"
    ls -lh "$RECORDING_DIR"/*.h264 2>/dev/null || echo "  (없음)"
    ;;
  *)
    echo "사용법: $0 {start|stop|status|list}"
    exit 1
    ;;
esac
