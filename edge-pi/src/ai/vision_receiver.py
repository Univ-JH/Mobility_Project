import socket
import threading
from src.communication.comm_config import (
    VISION_HOST, VISION_PORT,
    AI_ROAD_VAL, AI_SIDEWALK_VAL,
    CLASS_ROAD, CLASS_SIDEWALK,
)

# road_vision.py 신규 포맷: "road,0.87" / "sidewalk,0.43" / "unknown,0.0"
# 구버전 호환 포맷:           "1" (road) / "0" (sidewalk)
_NEW_FORMAT_ROAD     = "road"
_NEW_FORMAT_SIDEWALK = "sidewalk"
_NEW_FORMAT_UNKNOWN  = "unknown"

# unknown 수신 시 fail-safe: 신뢰도 0 으로 CLASS_SIDEWALK 반환
# → state_machine 이 VISION_CONFIDENCE_THRESHOLD 미달로 level_1 제동 적용
_UNKNOWN_CONFIDENCE = 0.0


class VisionReceiver:
    def __init__(self):
        self.host = VISION_HOST
        self.port = VISION_PORT

        self.current_surface = CLASS_ROAD
        self.current_confidence = 1.0
        self.is_running = False

        self.data_lock = threading.Lock()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
        except Exception as e:
            print(f"[비전] 소켓 바인딩 실패: {e}")

    def _parse(self, raw: str):
        """
        신규 포맷 "class,confidence" 와 구버전 "0"/"1" 양쪽 처리.
        Returns (surface_class, confidence) or (None, None) if unrecognised.
        """
        if "," in raw:
            parts = raw.split(",", 1)
            cls_str = parts[0]
            try:
                conf = float(parts[1])
            except ValueError:
                conf = 1.0

            if cls_str == _NEW_FORMAT_ROAD:
                return CLASS_ROAD, conf
            elif cls_str == _NEW_FORMAT_SIDEWALK:
                return CLASS_SIDEWALK, conf
            elif cls_str == _NEW_FORMAT_UNKNOWN:
                # Fail-safe: unknown → sidewalk with 0 confidence
                return CLASS_SIDEWALK, _UNKNOWN_CONFIDENCE
            return None, None

        # Backward-compatible legacy format
        if raw == AI_ROAD_VAL:
            return CLASS_ROAD, 1.0
        if raw == AI_SIDEWALK_VAL:
            return CLASS_SIDEWALK, 1.0
        return None, None

    def _listen_loop(self):
        print(f"[비전] AI 노면 데이터 수신 시작 ({self.host}:{self.port})")

        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(1024)
                val = data.decode("utf-8", errors="ignore").replace("\x00", "").strip()

                surface, confidence = self._parse(val)
                if surface is not None:
                    with self.data_lock:
                        self.current_surface    = surface
                        self.current_confidence = confidence

            except socket.timeout:
                continue
            except Exception:
                pass

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def get_surface_type(self) -> str:
        with self.data_lock:
            return self.current_surface

    def get_surface_confidence(self) -> float:
        with self.data_lock:
            return self.current_confidence

    def stop(self):
        self.is_running = False
        if hasattr(self, "thread"):
            self.thread.join()
        self.sock.close()
        print("[비전] 수신 모듈 안전 종료")