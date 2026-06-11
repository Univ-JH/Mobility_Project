import os
import threading
from datetime import datetime

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    _PICAM_OK = True
except ImportError:
    _PICAM_OK = False

from src.control.control_config import RECORDING_DIR


class VideoRecorder:
    """
    수동 또는 응급 트리거로 h264 영상을 파일로 저장하는 모듈.
    EMERGENCY_AUTO_RECORD=False(기본) → 자동 녹화 비활성.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._recording = False
        self._camera = None
        os.makedirs(RECORDING_DIR, exist_ok=True)
        print(f"📹 [녹화] 모듈 준비 완료 (저장 경로: {RECORDING_DIR})")

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, tag: str = "manual") -> bool:
        """녹화 시작. tag는 파일명 접두사 ('manual' 또는 'emergency')."""
        with self._lock:
            if self._recording:
                print("⚠️ [녹화] 이미 녹화 중")
                return False
            if not _PICAM_OK:
                print("⚠️ [녹화] picamera2 미설치 — pip install picamera2")
                return False
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(RECORDING_DIR, f"{tag}_{ts}.h264")
                self._camera = Picamera2()
                cfg = self._camera.create_video_configuration(
                    main={"size": (1280, 720), "format": "RGB888"}
                )
                self._camera.configure(cfg)
                encoder = H264Encoder(bitrate=4_000_000)
                self._camera.start_recording(encoder, FileOutput(path))
                self._recording = True
                print(f"🔴 [녹화] 시작: {path}")
                return True
            except Exception as e:
                print(f"⚠️ [녹화] 시작 실패: {e}")
                if self._camera:
                    try:
                        self._camera.close()
                    except Exception:
                        pass
                    self._camera = None
                return False

    def stop(self) -> bool:
        """녹화 중지."""
        with self._lock:
            if not self._recording:
                return False
            try:
                self._camera.stop_recording()
                self._camera.close()
                self._camera = None
                self._recording = False
                print("⏹️ [녹화] 종료")
                return True
            except Exception as e:
                print(f"⚠️ [녹화] 종료 실패: {e}")
                return False

    def check_flag_triggers(self):
        """메인 루프에서 매 tick 호출. 플래그 파일로 수동 녹화 제어.
        시작: touch /tmp/record_start
        중지: touch /tmp/record_stop
        """
        if os.path.exists("/tmp/record_start"):
            os.remove("/tmp/record_start")
            self.start(tag="manual")
        if os.path.exists("/tmp/record_stop"):
            os.remove("/tmp/record_stop")
            self.stop()

    def cleanup(self):
        self.stop()
        print("🧹 [녹화] 리소스 반환 완료")
