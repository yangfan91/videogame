"""
设备卡片组件。
"""
from datetime import datetime

from PyQt6.QtCore import QMimeData, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDrag, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from config import COLORS, COUNTDOWN_WARNING_SECS, DeviceStatus, TimerMode
from core import timer_alert
from core.timer_engine import TimerEngine


class DeviceCard(QFrame):
    """单设备卡片。"""

    DRAG_MIME_TYPE = "application/x-videogame-device-id"

    checkout_requested = pyqtSignal(int)
    add_time_requested = pyqtSignal(int)
    status_changed = pyqtSignal(int, str)

    def __init__(
        self,
        device_id: int,
        device_name: str,
        type_name: str,
        status: str = DeviceStatus.IDLE,
        parent=None,
    ):
        super().__init__(parent)
        self.device_id = device_id
        self.device_name = device_name
        self.type_name = type_name
        self._status = status

        self.timer = TimerEngine(device_id, parent=self)
        self.timer.tick.connect(self._on_tick)
        self.timer.expired.connect(self._on_expired)
        self.timer.warning.connect(self._on_warning)

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._blink_toggle)
        self._blink_state = False

        self._density_mode = "comfortable"
        self._card_frame_styles = {"base": "", "blink": ""}
        self._action_buttons: list[QPushButton] = []
        self._drag_start_pos: QPoint | None = None
        self._session_note = ""

        self._init_ui()
        self._apply_status_style()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._card_frame = QFrame()
        self._card_frame.setObjectName("cardFrame")
        outer.addWidget(self._card_frame)

        self._card_layout = QVBoxLayout(self._card_frame)
        self._card_layout.setContentsMargins(18, 18, 18, 18)
        self._card_layout.setSpacing(12)

        top_bar = QFrame()
        top_bar.setFixedHeight(3)
        top_bar.setObjectName("topBar")
        self._card_layout.addWidget(top_bar)
        self._accent_bar = top_bar

        self._header_frame = QFrame()
        self._header_frame.setFixedHeight(85)
        self._header_frame.setStyleSheet("background: transparent; border: none;")
        header = QVBoxLayout(self._header_frame)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_block = QFrame()
        title_block.setFixedHeight(58)
        title_block.setStyleSheet("background: transparent; border: none;")
        title_row = QHBoxLayout(title_block)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_left = QVBoxLayout()
        title_left.setSpacing(8)
        title_left.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.name_label = QLabel(self.device_name)
        self.name_label.setMinimumHeight(22)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.name_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLORS['text_dark']};"
        )
        title_left.addWidget(self.name_label)

        self.type_label = QLabel(self.type_name or "未分类")
        self.type_label.setFixedHeight(28)
        self.type_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_label.setStyleSheet(
            f"background: {COLORS['surface_alt']}; color: {COLORS['text_muted']}; "
            f"border: 1px solid {COLORS['border_soft']}; border-radius: 5px; "
            "padding: 4px 8px; font-size: 11px; font-weight: 600;"
        )
        title_left.addWidget(self.type_label, 0, Qt.AlignmentFlag.AlignLeft)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFixedHeight(24)

        self.mode_label = QLabel("待开始")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.mode_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600;"
        )

        self._status_column = QVBoxLayout()
        self._status_column.setSpacing(3)
        self._status_column.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._status_column.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignRight)
        self._status_column.addWidget(self.mode_label, 0, Qt.AlignmentFlag.AlignRight)
        self._status_column.addStretch()

        title_row.addLayout(title_left, 1)
        title_row.addLayout(self._status_column)
        header.addWidget(title_block)

        self.session_note_label = QLabel("")
        self.session_note_label.setObjectName("sessionNoteLabel")
        self.session_note_label.setFixedHeight(18)
        self.session_note_label.setToolTip("")
        self.session_note_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600;"
        )
        self.session_note_label.hide()
        header.addWidget(self.session_note_label)

        self._card_layout.addWidget(self._header_frame)

        self._timer_frame = QFrame()
        self._timer_frame.setObjectName("timerFrame")
        self._timer_frame.setStyleSheet(
            f"""
            QFrame#timerFrame {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border_soft']};
                border-radius: 8px;
            }}
            QFrame#timerFrame QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )
        timer_layout = QVBoxLayout(self._timer_frame)
        timer_layout.setContentsMargins(2, 22, 2, 4)
        timer_layout.setSpacing(4)
        self._timer_layout = timer_layout

        self._time_row_frame = QFrame()
        self._time_row_frame.setFixedHeight(48)
        self._time_row_frame.setStyleSheet("background: transparent; border: none;")
        time_row = QHBoxLayout(self._time_row_frame)
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(2)

        self.time_label = QLabel("--:--:--")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        time_row.addWidget(self.time_label, 1, Qt.AlignmentFlag.AlignBottom)

        self.time_context_label = QLabel("")
        self.time_context_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.time_context_label.setFixedHeight(24)
        self.time_context_label.setFixedWidth(52)
        self.time_context_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 700;"
        )
        self.time_context_label.hide()
        time_row.addWidget(self.time_context_label, 0, Qt.AlignmentFlag.AlignVCenter)
        timer_layout.addWidget(self._time_row_frame, 0, Qt.AlignmentFlag.AlignTop)

        self.runtime_hint_label = QLabel("")
        self.runtime_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.runtime_hint_label.setFixedHeight(18)
        self.runtime_hint_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
        )
        self.runtime_hint_label.hide()
        timer_layout.addWidget(self.runtime_hint_label)
        self._card_layout.addWidget(self._timer_frame)

        action_col = QVBoxLayout()
        action_col.setSpacing(8)

        primary_row = QHBoxLayout()
        primary_row.setSpacing(8)
        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(8)

        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.resume_btn = QPushButton("继续")
        self.add_time_btn = QPushButton("加时")
        self.checkout_btn = QPushButton("结账")

        self._action_buttons = [
            self.start_btn,
            self.pause_btn,
            self.resume_btn,
            self.add_time_btn,
            self.checkout_btn,
        ]

        for btn in self._action_buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(self._solid_btn_style(COLORS["accent"]))
        self.pause_btn.setStyleSheet(self._solid_btn_style(COLORS["warning"]))
        self.resume_btn.setStyleSheet(self._solid_btn_style(COLORS["success"]))
        self.add_time_btn.setStyleSheet(self._solid_btn_style(COLORS["countdown"]))
        self.checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkout_btn.setStyleSheet(self._outline_btn_style(COLORS["danger"]))

        self.checkout_btn.clicked.connect(
            lambda: self.checkout_requested.emit(self.device_id)
        )
        self.add_time_btn.clicked.connect(lambda: self.add_time_requested.emit(self.device_id))

        primary_row.addWidget(self.start_btn)
        primary_row.addWidget(self.pause_btn)
        primary_row.addWidget(self.resume_btn)
        secondary_row.addWidget(self.add_time_btn)
        secondary_row.addWidget(self.checkout_btn)

        action_col.addLayout(primary_row)
        action_col.addLayout(secondary_row)
        self._card_layout.addLayout(action_col)

        self.set_density_mode("comfortable")

    def _solid_btn_style(self, color: str) -> str:
        text_color = COLORS["accent_text"] if color == COLORS["accent"] else "white"
        return f"""
            QPushButton {{
                background: {color};
                color: {text_color};
                border: none;
                border-radius: 7px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {color};
            }}
            QPushButton:disabled {{
                background: {COLORS['border_soft']};
                color: #A7B0BE;
            }}
        """

    def _outline_btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['card_bg']};
                color: {color};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                border-color: {color};
                color: {color};
                background: {COLORS['surface']};
            }}
            QPushButton:disabled {{
                color: #A7B0BE;
                border-color: {COLORS['border_soft']};
            }}
        """

    def _apply_status_style(self):
        status_configs = {
            DeviceStatus.IDLE: {
                "text": "空闲",
                "accent": COLORS["text_muted"],
                "badge_bg": COLORS["surface_alt"],
                "border": COLORS["border"],
                "panel": COLORS["card_bg"],
                "alert": COLORS["card_bg"],
            },
            DeviceStatus.ACTIVE: {
                "text": "使用中",
                "accent": COLORS["accent"],
                "badge_bg": COLORS["surface_alt"],
                "border": "#245C66",
                "panel": COLORS["card_bg"],
                "alert": "#122936",
            },
            DeviceStatus.PAUSED: {
                "text": "已暂停",
                "accent": COLORS["warning"],
                "badge_bg": "#2A2112",
                "border": "#614518",
                "panel": COLORS["card_bg"],
                "alert": "#211A10",
            },
            DeviceStatus.EXPIRED: {
                "text": "已到时",
                "accent": COLORS["danger"],
                "badge_bg": "#2A1721",
                "border": "#563041",
                "panel": COLORS["card_bg"],
                "alert": "#21151C",
            },
            DeviceStatus.MAINTENANCE: {
                "text": "维护中",
                "accent": COLORS["maintenance"],
                "badge_bg": COLORS["surface_alt"],
                "border": COLORS["border"],
                "panel": COLORS["card_bg"],
                "alert": COLORS["surface"],
            },
        }
        cfg = status_configs.get(self._status, status_configs[DeviceStatus.IDLE])

        self._card_frame_styles["base"] = f"""
            QFrame#cardFrame {{
                background: {cfg['panel']};
                border: 1px solid {cfg['border']};
                border-radius: 8px;
            }}
        """
        self._card_frame_styles["blink"] = f"""
            QFrame#cardFrame {{
                background: {cfg['alert']};
                border: 1px solid {cfg['accent']};
                border-radius: 8px;
            }}
        """
        self._reset_blink_style()
        self._accent_bar.setStyleSheet(f"background: {cfg['accent']}; border: none;")
        self.status_label.setText(cfg["text"])
        self.status_label.setStyleSheet(
            f"background: {cfg['badge_bg']}; color: {cfg['accent']}; "
            "padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: 800;"
        )

        is_idle = self._status == DeviceStatus.IDLE
        is_active = self._status == DeviceStatus.ACTIVE
        is_paused = self._status == DeviceStatus.PAUSED
        is_expired = self._status == DeviceStatus.EXPIRED
        is_maintenance = self._status == DeviceStatus.MAINTENANCE
        is_countdown = self.timer.mode == TimerMode.COUNTDOWN

        self.start_btn.setVisible(is_idle)
        self.pause_btn.setVisible(is_active)
        self.resume_btn.setVisible(is_paused)
        self.add_time_btn.setVisible(is_countdown and (is_active or is_paused or is_expired))
        self.checkout_btn.setVisible(is_active or is_paused or is_expired)

        if is_idle:
            self.time_label.setText("--:--:--")
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.time_label.setStyleSheet(
                f"color: {COLORS['text_dark']}; font-weight: 700;"
            )
            self.mode_label.setText("待开始")
            self.time_context_label.clear()
            self.time_context_label.hide()
            self.runtime_hint_label.clear()
            self.runtime_hint_label.hide()
            self._set_session_note("")
        elif is_maintenance:
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.time_context_label.clear()
            self.time_context_label.hide()
            self.runtime_hint_label.clear()
            self.runtime_hint_label.hide()

        self._apply_time_label_style()

        for btn in self._action_buttons:
            btn.setEnabled(not is_maintenance)

        self._fit_time_font()

    def _reset_blink_style(self):
        self._blink_state = False
        self._card_frame.setStyleSheet(self._card_frame_styles["base"])

    def _set_status(self, status: str):
        self._status = status
        self._apply_status_style()
        self.status_changed.emit(self.device_id, status)

    def _on_tick(self, elapsed_seconds: int, remaining_seconds: int):
        self.time_label.setText(self._display_time_text())
        self._fit_time_font()
        self._update_runtime_hint(elapsed_seconds, remaining_seconds)

        self._apply_time_label_style(remaining_seconds)

    def _time_color(self, remaining_seconds: int | None = None) -> str:
        if self._status == DeviceStatus.IDLE:
            return COLORS["text_muted"]
        if self._status == DeviceStatus.PAUSED:
            return COLORS["text_muted"]
        if self._status == DeviceStatus.MAINTENANCE:
            return COLORS["text_muted"]
        if self.timer.mode == TimerMode.COUNTDOWN:
            if remaining_seconds is None:
                remaining_seconds = self.timer.get_remaining_seconds()
            if remaining_seconds <= 0:
                return COLORS["danger"]
            return COLORS["text_dark"]
        return COLORS["text_dark"]

    def _apply_time_label_style(self, remaining_seconds: int | None = None):
        self.time_label.setStyleSheet(
            f"color: {self._time_color(remaining_seconds)}; font-weight: 700;"
        )

    def _on_expired(self):
        self._set_status(DeviceStatus.EXPIRED)
        self._blink_timer.start()
        timer_alert.alert_expired(self.device_name)

    def _on_warning(self, remaining_seconds: int):
        timer_alert.alert_warning(self.device_name, max(1, remaining_seconds // 60))

    def _display_time_text(self) -> str:
        text = self.timer.get_display_time()
        if self.timer.mode == TimerMode.COUNTDOWN and text.startswith("-"):
            return text[1:]
        return text

    def _update_runtime_hint(self, elapsed_seconds: int, remaining_seconds: int):
        if self.timer.mode == TimerMode.COUNTDOWN:
            context = "超时时间" if remaining_seconds <= 0 else "剩余时间"
        else:
            context = "累计用时"
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_context_label.setText(context)
        self.time_context_label.show()
        self.runtime_hint_label.clear()
        self.runtime_hint_label.hide()

    def _set_session_note(self, note: str):
        self._session_note = note.strip()
        if self._session_note:
            text = f"备注：{self._session_note}"
            self.session_note_label.setText(text)
            self.session_note_label.setToolTip(text)
            self.session_note_label.show()
        else:
            self.session_note_label.clear()
            self.session_note_label.setToolTip("")
            self.session_note_label.hide()

    def _blink_toggle(self):
        self._blink_state = not self._blink_state
        self._card_frame.setStyleSheet(
            self._card_frame_styles["blink" if self._blink_state else "base"]
        )

    def _fit_time_font(self):
        width = self.time_label.width()
        if width <= 0:
            return
        text = self.time_label.text() or "--:--:--"
        base_size = 34 if self._density_mode == "comfortable" else 30
        for point_size in range(base_size, 13, -1):
            font = QFont("Consolas", point_size)
            font.setBold(True)
            if QFontMetrics(font).horizontalAdvance(text) <= max(80, width - 2):
                self.time_label.setFont(font)
                self.time_label.setFixedHeight(48 if self._density_mode == "comfortable" else 40)
                return

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_time_font()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_time_font()

    def _event_pos(self, event) -> QPoint:
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def _drag_mime_data(self) -> QMimeData:
        mime = QMimeData()
        mime.setData(self.DRAG_MIME_TYPE, str(self.device_id).encode("utf-8"))
        return mime

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = self._event_pos(event)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)
            return
        if self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return

        distance = (self._event_pos(event) - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        drag = QDrag(self)
        drag.setMimeData(self._drag_mime_data())
        drag.exec(Qt.DropAction.MoveAction)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._drag_start_pos = None

    def start_timer(
        self,
        session_id: int,
        mode: str = TimerMode.FREEPLAY,
        countdown_seconds: int = 0,
        start_time: datetime | None = None,
        pause_duration: int = 0,
        note: str = "",
    ):
        mode_text = TimerMode.LABELS.get(mode, "")
        self.mode_label.setText(mode_text)
        self.mode_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 700;"
        )
        self._set_session_note(note)
        self.timer.start(
            session_id,
            mode=mode,
            countdown_seconds=countdown_seconds,
            start_time=start_time,
            pause_duration=pause_duration,
        )
        self.time_label.setText(self._display_time_text())
        self._update_runtime_hint(
            self.timer.get_elapsed_seconds(), self.timer.get_remaining_seconds()
        )
        self._set_status(DeviceStatus.ACTIVE)

    def pause_timer(self):
        self._blink_timer.stop()
        self._reset_blink_style()
        self.timer.pause()
        self.runtime_hint_label.clear()
        self.runtime_hint_label.hide()
        self._set_status(DeviceStatus.PAUSED)

    def resume_timer(self, pause_duration: int = 0):
        self.timer.resume(pause_duration)
        if self._status != DeviceStatus.EXPIRED:
            self._set_status(DeviceStatus.ACTIVE)
        else:
            self._blink_timer.start()

    def add_time(self, extra_seconds: int):
        self.timer.add_time(extra_seconds)
        if self._status == DeviceStatus.EXPIRED:
            self._blink_timer.stop()
            self._set_status(DeviceStatus.ACTIVE)

    def stop_timer(self) -> int:
        self._blink_timer.stop()
        self._reset_blink_style()
        elapsed = self.timer.stop()
        self.timer.reset()
        self.mode_label.setText("待开始")
        self._set_session_note("")
        self._set_status(DeviceStatus.IDLE)
        return elapsed

    def set_maintenance(self, is_maintenance: bool):
        if is_maintenance:
            self._set_status(DeviceStatus.MAINTENANCE)
        else:
            self._set_status(DeviceStatus.IDLE)

    def set_density_mode(self, mode: str):
        self._density_mode = "compact" if mode == "compact" else "comfortable"
        if self._density_mode == "compact":
            self.setFixedSize(260, 286)
            btn_height = 32
            timer_height = 86
            time_row_height = 40
        else:
            self.setFixedSize(292, 326)
            btn_height = 36
            timer_height = 96
            time_row_height = 48
        self._timer_frame.setFixedHeight(timer_height)
        self._time_row_frame.setFixedHeight(time_row_height)
        for btn in self._action_buttons:
            btn.setFixedHeight(btn_height)
        self._fit_time_font()

    def restore_session(
        self,
        session_id: int,
        mode: str,
        countdown_seconds: int,
        start_time: datetime,
        pause_duration: int,
        is_paused: bool,
        is_expired: bool = False,
        note: str = "",
    ):
        self.start_timer(
            session_id,
            mode=mode,
            countdown_seconds=countdown_seconds,
            start_time=start_time,
            pause_duration=pause_duration,
            note=note,
        )
        if is_expired:
            self._on_expired()
        elif is_paused:
            self.pause_timer()

    @property
    def current_session_id(self) -> int:
        return self.timer.session_id

    @property
    def current_elapsed(self) -> int:
        return self.timer.get_elapsed_seconds()
