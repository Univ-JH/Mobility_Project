import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


_STATE_STYLE = {
    "NORMAL":               "bold green",
    "ZONE_VIOLATION":       "bold yellow",
    "REAR_APPROACH_WARNING": "bold yellow",
    "UNCERTAIN_ENVIRONMENT": "yellow",
    "RIDER_EMERGENCY":      "bold red",
    "INITIALIZING":         "dim",
}

_BRAKE_STYLE = {
    "level_0":         ("● SAFE",      "green"),
    "level_1":         ("▲ CAUTION",   "yellow"),
    "level_2":         ("⚠ WARNING",   "dark_orange"),
    "level_emergency": ("🚨 EMERGENCY", "red"),
}

_LOG_STYLE = {
    "INFO":  "white",
    "WARN":  "yellow",
    "ERROR": "red",
    "STATE": "cyan",
    "MQTT":  "blue",
}


class SystemDashboard:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self._start_time = time.time()
        self._lock = threading.Lock()

        self._state = "INITIALIZING"
        self._brake_level = "level_0"
        self._reason = "시스템 초기화 중..."
        self._sensors: Dict[str, Any] = {}
        self._ble_connected = False
        self._mqtt_connected = False
        self._events: deque = deque(maxlen=20)

        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── public update API ─────────────────────────────────────────────────────

    def update_state(self, state: str, brake_level: str, reason: str):
        with self._lock:
            prev = self._state
            self._state = state
            self._brake_level = brake_level
            self._reason = reason
            if prev != state:
                self._log_locked(f"상태 전이: {prev} → {state}  ({reason})", "STATE")

    def update_sensors(self, data: Dict[str, Any]):
        with self._lock:
            self._sensors = data.copy()

    def update_ble(self, connected: bool, helmet_id: str = ""):
        with self._lock:
            prev = self._ble_connected
            self._ble_connected = connected
            if prev != connected:
                label = f"BLE {'연결' if connected else '끊김'}" + (f" ({helmet_id})" if helmet_id else "")
                self._log_locked(label, "WARN" if not connected else "INFO")

    def update_mqtt(self, connected: bool):
        with self._lock:
            self._mqtt_connected = connected

    def log(self, msg: str, level: str = "INFO"):
        with self._lock:
            self._log_locked(msg, level)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="TUI")
        self._thread.start()

    def stop(self):
        self._running = False

    # ── internals ─────────────────────────────────────────────────────────────

    def _log_locked(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self._events.appendleft((ts, level, msg))

    def _uptime(self) -> str:
        secs = int(time.time() - self._start_time)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _build(self):
        with self._lock:
            state      = self._state
            brake      = self._brake_level
            reason     = self._reason
            sensors    = self._sensors.copy()
            ble_ok     = self._ble_connected
            mqtt_ok    = self._mqtt_connected
            events     = list(self._events)

        # ── header ───────────────────────────────────────────────────────────
        header = Panel(
            Text.assemble(
                ("🚲 Smart Bike Safety System", "bold white"),
                "  │  ",
                (self.device_id, "cyan"),
                "  │  Uptime: ",
                (self._uptime(), "green"),
            ),
            style="on grey11",
        )

        # ── state panel ───────────────────────────────────────────────────────
        state_style = _STATE_STYLE.get(state, "white")
        brake_label, brake_style = _BRAKE_STYLE.get(brake, ("?", "white"))

        st = Table.grid(padding=(0, 1))
        st.add_column(style="dim", width=10)
        st.add_column()

        st.add_row("상태", Text(state, style=state_style))
        st.add_row("제동", Text(brake_label, style=brake_style))
        st.add_row("원인", Text(reason[:45], style="italic"))
        st.add_row("", "")
        st.add_row(
            "BLE",
            Text("● 연결됨" if ble_ok else "○ 끊김",
                 style="green" if ble_ok else "red"),
        )
        st.add_row(
            "MQTT",
            Text("● 연결됨" if mqtt_ok else "○ 끊김",
                 style="green" if mqtt_ok else "red"),
        )

        state_panel = Panel(st, title="[bold]시스템 상태[/bold]", border_style="bright_blue")

        # ── sensor panel ──────────────────────────────────────────────────────
        speed   = sensors.get("speed", 0.0)
        surface = sensors.get("surface_class", "-")
        conf    = sensors.get("confidence", 0.0)
        worn    = sensors.get("is_worn", False)
        accident= sensors.get("is_accident", False)
        rear    = sensors.get("rear_approach", False)
        lat     = sensors.get("lat", 0.0)
        lon     = sensors.get("lon", 0.0)

        sn = Table.grid(padding=(0, 1))
        sn.add_column(style="dim", width=10)
        sn.add_column()

        sn.add_row("속도",   Text(f"{speed:.1f} km/h", style="cyan"))
        sn.add_row("노면",   Text(f"{surface}  ({conf:.0%})",
                                  style="yellow" if surface == "sidewalk" else "green"))
        sn.add_row("헬멧",   Text("✓ 착용" if worn else "✗ 미착용",
                                  style="green" if worn else "red"))
        sn.add_row("충격",   Text("⚠ 감지됨" if accident else "없음",
                                  style="red" if accident else "green"))
        sn.add_row("후방",   Text("⚠ 접근" if rear else "이상없음",
                                  style="yellow" if rear else "green"))
        sn.add_row("GPS",    Text(f"{lat:.5f}, {lon:.5f}", style="dim"))

        sensor_panel = Panel(sn, title="[bold]센서[/bold]", border_style="bright_blue")

        middle = Columns([state_panel, sensor_panel], equal=True, expand=True)

        # ── events log ───────────────────────────────────────────────────────
        log_text = Text()
        for ts, lvl, msg in events[:12]:
            style = _LOG_STYLE.get(lvl, "white")
            log_text.append(f"[{ts}] ", style="dim")
            log_text.append(f"{lvl:<5} ", style=style)
            log_text.append(msg + "\n", style="white")

        events_panel = Panel(log_text, title="[bold]이벤트 로그[/bold]",
                             border_style="bright_blue")

        return Group(header, middle, events_panel)

    def _run(self):
        console = Console()
        with Live(self._build(), console=console, refresh_per_second=4,
                  screen=False, transient=False) as live:
            while self._running:
                live.update(self._build())
                time.sleep(0.25)
