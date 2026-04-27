
import sys, os
_PLUGIN_DIR = os.path.join(os.path.expanduser("~"), "houdini_tg_notifier")
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from tg_notifier import get_notifier, send_telegram
import hou

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    from PySide6 import QtWidgets, QtCore


class TGNotifierPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifier = get_notifier()
        self._build_ui()
        self._load_into_ui()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(2000)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        title = QtWidgets.QLabel("Houdini - Telegram Notifier")
        title.setStyleSheet("font-size: 13px; font-weight: bold;")
        root.addWidget(title)

        grp = QtWidgets.QGroupBox("Telegram Bot")
        form = QtWidgets.QFormLayout(grp)
        self.le_token = QtWidgets.QLineEdit()
        self.le_token.setPlaceholderText("123456:ABC-DEF...")
        self.le_token.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("Bot Token:", self.le_token)
        self.le_chat = QtWidgets.QLineEdit()
        self.le_chat.setPlaceholderText("-100123456789")
        form.addRow("Chat ID:", self.le_chat)
        btn_test = QtWidgets.QPushButton("Test")
        btn_test.setFixedWidth(80)
        btn_test.clicked.connect(self._test_send)
        form.addRow("", btn_test)
        root.addWidget(grp)

        grp2 = QtWidgets.QGroupBox("What to send")
        fl = QtWidgets.QVBoxLayout(grp2)
        self.cb_errors   = QtWidgets.QCheckBox("Errors (Error / Fatal)")
        self.cb_warnings = QtWidgets.QCheckBox("Warnings")
        self.cb_messages = QtWidgets.QCheckBox("Messages")
        self.cb_render   = QtWidgets.QCheckBox("Render complete events")
        self.cb_scene    = QtWidgets.QCheckBox("Include scene name")
        for cb in (self.cb_errors, self.cb_warnings, self.cb_messages, self.cb_render, self.cb_scene):
            fl.addWidget(cb)
        root.addWidget(grp2)

        grp3 = QtWidgets.QGroupBox("Options")
        gl = QtWidgets.QFormLayout(grp3)
        self.sp_cooldown = QtWidgets.QSpinBox()
        self.sp_cooldown.setRange(1, 3600)
        self.sp_cooldown.setSuffix(" sec")
        gl.addRow("Cooldown:", self.sp_cooldown)
        root.addWidget(grp3)

        row = QtWidgets.QHBoxLayout()
        self.btn_toggle = QtWidgets.QPushButton("Start Monitor")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self._toggle_monitor)
        btn_save = QtWidgets.QPushButton("Save")
        btn_save.clicked.connect(self._save)
        btn_log = QtWidgets.QPushButton("Send Log")
        btn_log.clicked.connect(self._send_last)
        row.addWidget(self.btn_toggle)
        row.addWidget(btn_save)
        row.addWidget(btn_log)
        root.addLayout(row)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)
        root.addStretch()

    def _load_into_ui(self):
        s = self.notifier.settings
        self.le_token.setText(s.get("bot_token", ""))
        self.le_chat.setText(s.get("chat_id", ""))
        self.cb_errors.setChecked(s.get("send_errors", True))
        self.cb_warnings.setChecked(s.get("send_warnings", True))
        self.cb_messages.setChecked(s.get("send_messages", True))
        self.cb_render.setChecked(s.get("send_render", True))
        self.cb_scene.setChecked(s.get("scene_name_in_msg", True))
        self.sp_cooldown.setValue(s.get("cooldown", 15))
        active = self.notifier._active
        self.btn_toggle.setChecked(active)
        self.btn_toggle.setText("Stop Monitor" if active else "Start Monitor")

    def _collect(self):
        return dict(
            bot_token=self.le_token.text().strip(),
            chat_id=self.le_chat.text().strip(),
            send_errors=self.cb_errors.isChecked(),
            send_warnings=self.cb_warnings.isChecked(),
            send_messages=self.cb_messages.isChecked(),
            send_render=self.cb_render.isChecked(),
            scene_name_in_msg=self.cb_scene.isChecked(),
            cooldown=self.sp_cooldown.value(),
        )

    def _save(self):
        self.notifier.update_settings(**self._collect())
        self._status("Settings saved", "green")

    def _toggle_monitor(self, checked):
        self.notifier.update_settings(**self._collect())
        if checked:
            ok, msg = self.notifier.start()
            self.btn_toggle.setText("Stop Monitor")
            self._status(msg, "green" if ok else "orange")
        else:
            self.notifier.stop()
            self.btn_toggle.setText("Start Monitor")
            self._status("Monitor stopped", "gray")

    def _test_send(self):
        self.notifier.update_settings(**self._collect())
        s = self.notifier.settings
        ok, err = send_telegram(
            s["bot_token"], s["chat_id"],
            "<b>Houdini TG Notifier</b>\nTest message - connection OK!"
        )
        self._status("Test sent" if ok else "Error: {}".format(err),
                     "green" if ok else "red")

    def _send_last(self):
        ok, msg = self.notifier.send_last_errors(n=15)
        self._status(msg, "green" if ok else "red")

    def _refresh_status(self):
        active = self.notifier._active
        self.btn_toggle.setChecked(active)
        self.btn_toggle.setText("Stop Monitor" if active else "Start Monitor")

    def _status(self, text, color="gray"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet("color: {}; padding: 3px;".format(color))


def createInterface():
    return TGNotifierPanel()
