import socket
import threading
from src.communication.comm_config import (
    VISION_HOST, VISION_PORT, 
    AI_ROAD_VAL, AI_SIDEWALK_VAL,
    CLASS_ROAD, CLASS_SIDEWALK
)

class VisionReceiver:
    def __init__(self):
        self.host = VISION_HOST
        self.port = VISION_PORT
        
        # State Machine과 동일한 초기값 설정
        self.current_surface = CLASS_ROAD 
        self.is_running = False
        
        # 스레드 안전성(Thread Safety)을 위한 자물쇠
        self.data_lock = threading.Lock()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
        except Exception as e:
            print(f"⚠️ [비전] 소켓 바인딩 실패: {e}")

    def _listen_loop(self):
        print(f"👁️ [비전] AI 노면 데이터 수신 시작 ({self.host}:{self.port})")
        
        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(1024)
                # 눈에 보이지 않는 찌꺼기 데이터(\x00) 완벽 제거
                val = data.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                
                new_surface = None
                if val == AI_ROAD_VAL:
                    new_surface = CLASS_ROAD
                elif val == AI_SIDEWALK_VAL:
                    new_surface = CLASS_SIDEWALK
                
                # 유효한 값이 들어왔을 때만 자물쇠를 걸고 안전하게 업데이트
                if new_surface:
                    with self.data_lock:
                        self.current_surface = new_surface
                        
            except socket.timeout:
                continue 
            except Exception:
                pass

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def get_surface_type(self):
        """메인 로직에서 안전하게 값을 꺼내갈 때 사용합니다."""
        with self.data_lock:
            return self.current_surface

    def stop(self):
        self.is_running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        self.sock.close()
        print("🧹 [비전] 수신 모듈 안전 종료")