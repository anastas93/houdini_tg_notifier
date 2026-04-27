
import hou
import threading
import time
import urllib.request
import json
import os
import re
from datetime import datetime

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".houdini_tg_notifier.json")

DEFAULT_SETTINGS = {
    "bot_token": "",
    "chat_id": "",
    "send_errors":   True,
    "send_warnings": True,
    "send_messages": True,
    "send_render":   True,
    "scene_name_in_msg": True,
    "monitor_enabled": False,
    "cooldown": 15,
}

RENDER_PATTERNS = [
    re.compile(r, re.IGNORECASE) for r in [
        r"render\s+complete",
        r"rendered?\s+frame",
        r"mantra.*finished",
        r"karma.*finished",
        r"rendering\s+done",
        r"ifd.*written",
        r"render\s+time\s*:",
        r"frame\s+\d+.*done",
        r"cook\s+complete",
    ]
]


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = DEFAULT_SETTINGS.copy()
        s.update(data)
        return s
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def send_telegram(token, chat_id, text):
    if not token or not chat_id:
        return False, "bot_token or chat_id not set"
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return (True, "") if result.get("ok") else (False, str(result))
    except Exception as e:
        return False, str(e)


def _make_sink_class(callback):
    class _Sink(hou.logging.LogSink):
        def emit(self, entry):
            callback(entry.severity(), entry.message(),
                     getattr(entry, "source", lambda: "")())
    return _Sink


class TGNotifier:
    def __init__(self):
        self.settings = load_settings()
        self._last_sent = {}
        self._lock = threading.Lock()
        self._sink = None
        self._active = False
        self._history = []
        self._history_max = 100
        if self.settings.get("monitor_enabled"):
            self.start()

    def start(self):
        if self._active:
            return True, "Already running"
        ok = self._attach_log_sink()
        self._attach_render_callbacks()
        self._active = True
        self.settings["monitor_enabled"] = True
        save_settings(self.settings)
        return ok, ("Monitor started" if ok else "Started in fallback mode")

    def stop(self):
        self._detach_log_sink()
        self._detach_render_callbacks()
        self._active = False
        self.settings["monitor_enabled"] = False
        save_settings(self.settings)

    def _attach_log_sink(self):
        try:
            SinkClass = _make_sink_class(self._on_entry)
            self._sink = SinkClass()
            hou.logging.addLogSink(self._sink)
            return True
        except AttributeError:
            self._start_file_monitor()
            return False

    def _detach_log_sink(self):
        if self._sink:
            try:
                hou.logging.removeLogSink(self._sink)
            except Exception:
                pass
            self._sink = None

    def _attach_render_callbacks(self):
        try:
            hou.hipFile.addEventCallback(self._on_hip_event)
        except Exception:
            pass

    def _detach_render_callbacks(self):
        try:
            hou.hipFile.removeEventCallback(self._on_hip_event)
        except Exception:
            pass

    def _on_hip_event(self, event_type):
        pass

    def _start_file_monitor(self):
        log_path = os.path.join(
            hou.getenv("HOUDINI_TEMP_DIR") or hou.homeHoudiniDirectory(),
            "houdini.log"
        )
        if not os.path.exists(log_path):
            return
        pos = [os.path.getsize(log_path)]
        _SEV_RE = re.compile(r"\b(Fatal|Error|Warning|Message)\b", re.IGNORECASE)

        def _poll():
            while self._active:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos[0])
                        chunk = f.read()
                        pos[0] = f.tell()
                    if chunk:
                        for line in chunk.splitlines():
                            m = _SEV_RE.search(line)
                            sev_str = m.group(1).lower() if m else "message"
                            sev = {
                                "fatal":   hou.severityType.Fatal,
                                "error":   hou.severityType.Error,
                                "warning": hou.severityType.Warning,
                            }.get(sev_str, hou.severityType.Message)
                            self._on_entry(sev, line)
                except Exception:
                    pass
                time.sleep(2)

        threading.Thread(target=_poll, daemon=True).start()

    def _on_entry(self, severity, message, source=""):
        s = self.settings
        with self._lock:
            self._history.append((severity, message))
            if len(self._history) > self._history_max:
                self._history.pop(0)

        is_render = any(p.search(message) for p in RENDER_PATTERNS)

        want = False
        if is_render and s.get("send_render", True):
            want = True
        elif severity in (hou.severityType.Error, hou.severityType.Fatal) and s["send_errors"]:
            want = True
        elif severity == hou.severityType.Warning and s["send_warnings"]:
            want = True
        elif severity == hou.severityType.Message and s["send_messages"]:
            want = True

        if not want:
            return

        with self._lock:
            now = time.time()
            key = message[:100]
            if now - self._last_sent.get(key, 0) < s["cooldown"]:
                return
            self._last_sent[key] = now

        threading.Thread(
            target=self._send,
            args=(severity, message, source, is_render),
            daemon=True
        ).start()

    def _send(self, severity, message, source="", is_render=False):
        s = self.settings
        if is_render:
            icon, label = "OK", "RENDER"
        else:
            icon, label = {
                hou.severityType.Fatal:   ("!!", "FATAL"),
                hou.severityType.Error:   ("X",  "ERROR"),
                hou.severityType.Warning: ("!",  "WARNING"),
                hou.severityType.Message: ("i",  "MESSAGE"),
            }.get(severity, ("-", "INFO"))

        scene = ""
        if s.get("scene_name_in_msg"):
            try:
                scene = "\n<b>Scene:</b> {}".format(os.path.basename(hou.hipFile.name()))
            except Exception:
                pass

        ts = datetime.now().strftime("%H:%M:%S")
        text = "[{}] <b>{}</b>\n<b>Time:</b> {}{}\n<code>{}</code>".format(
            icon, label, ts, scene, message[:800]
        )
        if source:
            text += "\n<i>Source: {}</i>".format(source)

        send_telegram(s["bot_token"], s["chat_id"], text)

    def send_last_errors(self, n=15):
        try:
            entries = list(hou.logging.logEntries())[-n:]
            if not entries:
                return True, "No log entries"
            lines = []
            for e in entries:
                sev = e.severity()
                tag = {
                    hou.severityType.Fatal:   "FATAL",
                    hou.severityType.Error:   "ERR",
                    hou.severityType.Warning: "WARN",
                }.get(sev, "MSG")
                lines.append("[{}] {}".format(tag, e.message()[:200]))
        except Exception:
            with self._lock:
                raw = self._history[-n:]
            if not raw:
                return True, "History empty"
            lines = []
            for sev, msg in raw:
                tag = {
                    hou.severityType.Fatal:   "FATAL",
                    hou.severityType.Error:   "ERR",
                    hou.severityType.Warning: "WARN",
                }.get(sev, "MSG")
                lines.append("[{}] {}".format(tag, msg[:200]))

        s = self.settings
        scene = ""
        if s.get("scene_name_in_msg"):
            try:
                scene = "\n<b>Scene:</b> {}".format(os.path.basename(hou.hipFile.name()))
            except Exception:
                pass
        text = "<b>Houdini Log</b>{}\n\n<code>{}</code>".format(
            scene, "\n".join(lines)
        )
        return send_telegram(s["bot_token"], s["chat_id"], text)

    def update_settings(self, **kwargs):
        self.settings.update(kwargs)
        save_settings(self.settings)


_instance = None

def get_notifier():
    global _instance
    if _instance is None:
        _instance = TGNotifier()
    return _instance
