"""
包厢面板（v2）
管理所有包厢卡片，处理开始/暂停/恢复/结束逻辑。
开始计时时弹出模式选择对话框（团购套餐 or 自由计时）。
"""
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QScrollArea, QGridLayout, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame,
    QApplication, QDialog, QLineEdit, QPushButton, QSizePolicy,
    QComboBox, QTextEdit
)
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QIntValidator

from ui.device_card import DeviceCard
from ui.checkout_dialog import CheckoutDialog
from ui.message_box import show_critical, show_warning
from ui.window_chrome import apply_dark_title_bar
from database import db_manager as db
from config import ASSETS_DIR, COLORS, DeviceStatus, SessionStatus, TimerMode


BUTTON_PLAY_ICON = Path(ASSETS_DIR, "button_play.svg").as_posix()


# ─────────────────────────────────────────────
# 开始计时模式选择对话框（重新设计）
# ─────────────────────────────────────────────

class StartTimerDialog(QDialog):
    """
    开始计时前选择模式：
    - 团购套餐（倒计时）：大按钮选择套餐时长
    - 自由计时（正计时）：直接开始
    """

    # 两种模式对应的对话框高度
    _HEIGHT_FREEPLAY   = 348   # 自由计时：模式选择 + 备注 + 按钮
    _HEIGHT_COUNTDOWN  = 628   # 团购套餐：模式选择 + 套餐区 + 备注 + 按钮

    def __init__(self, device_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"开始计时 — {device_name}")
        self.setFixedWidth(440)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['background']}; }}")
        apply_dark_title_bar(self)

        self.selected_mode: str = TimerMode.FREEPLAY
        self.countdown_minutes: int = 0
        self.note: str = ""
        self._active_mins: int = 0   # 当前选中的套餐分钟数

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 标题栏 ──
        title_bar = QFrame()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(f"background: {COLORS['primary']};")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)
        title_lbl = QLabel("🎮  选择计时模式")
        title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(title_lbl)
        layout.addWidget(title_bar)

        body = QFrame()
        body.setStyleSheet(f"background: {COLORS['background']};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 18, 20, 18)
        body_layout.setSpacing(18)

        # ── 模式选择区（两个大按钮） ──
        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)

        self._btn_freeplay   = self._make_mode_btn(
            "🎮", "自由计时", "先玩后结账\n结束时显示时长",
            COLORS['secondary']
        )
        self._btn_countdown  = self._make_mode_btn(
            "⏱️", "团购套餐", "倒计时，到时提醒\n请选择套餐时长",
            COLORS['countdown']
        )
        self._btn_freeplay.clicked.connect(lambda: self._select_mode(TimerMode.FREEPLAY))
        self._btn_countdown.clicked.connect(lambda: self._select_mode(TimerMode.COUNTDOWN))

        mode_row.addWidget(self._btn_freeplay)
        mode_row.addWidget(self._btn_countdown)
        body_layout.addLayout(mode_row)

        # ── 套餐时长选择区（始终占位，切换可见性不改变对话框大小） ──
        self._countdown_frame = QFrame()
        self._countdown_frame.setObjectName("countdownPanel")
        self._countdown_frame.setStyleSheet(f"""
            QFrame#countdownPanel {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['countdown']};
                border-radius: 8px;
            }}
        """)
        cd_layout = QVBoxLayout(self._countdown_frame)
        cd_layout.setContentsMargins(16, 12, 16, 12)
        cd_layout.setSpacing(10)

        cd_title = QLabel("选择套餐时长")
        cd_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cd_title.setStyleSheet(
            f"color: {COLORS['countdown']}; font-size: 13px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        cd_layout.addWidget(cd_title)

        # 快捷时长大按钮
        preset_row1 = QHBoxLayout()
        preset_row1.setSpacing(8)
        preset_row2 = QHBoxLayout()
        preset_row2.setSpacing(8)

        self._preset_btns: dict[int, QPushButton] = {}
        for i, mins in enumerate([30, 60, 90, 120, 150, 180]):
            btn = self._make_preset_btn(mins)
            self._preset_btns[mins] = btn
            if i < 3:
                preset_row1.addWidget(btn)
            else:
                preset_row2.addWidget(btn)

        cd_layout.addLayout(preset_row1)
        cd_layout.addLayout(preset_row2)

        # 自定义时长：纯数字输入框 + 外部「分钟」标签 + 加减按钮
        custom_row = QHBoxLayout()
        custom_row.setSpacing(6)

        custom_lbl = QLabel("自定义：")
        custom_lbl.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 13px; "
            "background: transparent; border: none;"
        )

        # 减号按钮
        self._minus_btn = QPushButton("－")
        self._minus_btn.setFixedSize(36, 36)
        self._minus_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 18px;
                font-weight: bold;
                color: {COLORS['text_dark']};
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; }}
            QPushButton:pressed {{ background: {COLORS['surface_alt']}; }}
        """)
        self._minus_btn.clicked.connect(lambda: self._adjust_custom(-1))

        # 纯数字输入框
        self._custom_edit = QLineEdit("60")
        self._custom_edit.setValidator(QIntValidator(1, 600))
        self._custom_edit.setFixedSize(64, 36)
        self._custom_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 18px;
                font-weight: bold;
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
            }}
            QLineEdit:focus {{ border-color: {COLORS['countdown']}; }}
        """)
        self._custom_edit.textChanged.connect(self._on_custom_changed)

        # 加号按钮
        self._plus_btn = QPushButton("＋")
        self._plus_btn.setFixedSize(36, 36)
        self._plus_btn.setStyleSheet(self._minus_btn.styleSheet())
        self._plus_btn.clicked.connect(lambda: self._adjust_custom(1))

        # 「分钟」标签
        mins_lbl = QLabel("分钟")
        mins_lbl.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 14px; font-weight: bold; "
            "background: transparent; border: none;"
        )

        custom_row.addWidget(custom_lbl)
        custom_row.addStretch()
        custom_row.addWidget(self._minus_btn)
        custom_row.addWidget(self._custom_edit)
        custom_row.addWidget(self._plus_btn)
        custom_row.addWidget(mins_lbl)
        cd_layout.addLayout(custom_row)

        # 当前选中时长显示
        self._selected_time_lbl = QLabel("未选择")
        self._selected_time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._selected_time_lbl.setStyleSheet(
            f"color: {COLORS['countdown']}; font-size: 22px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        cd_layout.addWidget(self._selected_time_lbl)

        # 套餐区默认隐藏，切换模式时通过 setVisible + setFixedHeight 控制
        self._countdown_frame.setVisible(False)
        body_layout.addWidget(self._countdown_frame)

        body_layout.addSpacing(18)

        note_label = QLabel("备注（可选）：")
        note_label.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 13px;")
        body_layout.addWidget(note_label)

        self._note_input = QTextEdit()
        self._note_input.setPlaceholderText("如：团购码、客户要求、赠送时长等")
        self._note_input.setFixedHeight(72)
        self._note_input.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 13px;
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
            }}
            QTextEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)
        body_layout.addWidget(self._note_input)

        layout.addWidget(body)

        # ── 按钮区 ──
        btn_bar = QFrame()
        btn_bar.setStyleSheet(
            f"background: {COLORS['card_bg']}; border-top: 1px solid {COLORS['border_soft']};"
        )
        btn_bar_layout = QHBoxLayout(btn_bar)
        btn_bar_layout.setContentsMargins(20, 12, 20, 12)
        btn_bar_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                color: {COLORS['text_dark']};
                font-size: 13px;
                padding: 0 20px;
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['accent']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        self._start_btn = QPushButton("开始计时")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setFixedHeight(40)
        self._start_btn.setEnabled(False)
        self._start_btn.setIcon(QIcon(BUTTON_PLAY_ICON))
        self._start_btn.setIconSize(QSize(18, 18))
        self._start_btn.setProperty("usesVectorStartIcon", True)
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                border: none;
                border-radius: 7px;
                color: {COLORS['accent_text']};
                font-size: 14px;
                font-weight: bold;
                padding: 0 24px;
            }}
            QPushButton:hover:!disabled {{
                background: #A7FBFF;
            }}
            QPushButton:pressed:!disabled {{
                background: #5DE8F0;
            }}
            QPushButton:disabled {{
                background: {COLORS['border_soft']};
                color: #A7B0BE;
            }}
        """)
        self._start_btn.clicked.connect(self._on_start)

        btn_bar_layout.addWidget(cancel_btn)
        btn_bar_layout.addStretch()
        btn_bar_layout.addWidget(self._start_btn)
        layout.addWidget(btn_bar)

        # 默认选中自由计时
        self._select_mode(TimerMode.FREEPLAY)

    # ─────────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────────

    def _make_mode_btn(self, icon: str, title: str,
                       desc: str, color: str) -> QPushButton:
        btn = QPushButton(f"{icon}\n{title}\n{desc}")
        btn.setFixedHeight(96)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setCheckable(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_dark']};
                font-size: 12px;
                text-align: center;
                padding: 8px;
            }}
            QPushButton:checked {{
                background: {COLORS['surface_alt']};
                border: 2px solid {color};
                color: #FFFFFF;
                font-weight: bold;
            }}
            QPushButton:hover:!checked {{
                border-color: {color};
                background: {COLORS['surface_alt']};
            }}
        """)
        return btn

    def _make_preset_btn(self, mins: int) -> QPushButton:
        h = mins // 60
        m = mins % 60
        if h > 0 and m > 0:
            label = f"{h}小时{m}分"
        elif h > 0:
            label = f"{h}小时"
        else:
            label = f"{m}分钟"

        btn = QPushButton(label)
        btn.setFixedHeight(44)
        btn.setCheckable(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                color: {COLORS['text_dark']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background: {COLORS['countdown']};
                border-color: {COLORS['countdown']};
                color: white;
            }}
            QPushButton:hover:!checked {{
                border-color: {COLORS['countdown']};
                color: {COLORS['countdown']};
            }}
        """)
        btn.clicked.connect(lambda checked, m=mins: self._select_preset(m))
        return btn

    def _select_mode(self, mode: str):
        self.selected_mode = mode
        is_countdown = (mode == TimerMode.COUNTDOWN)

        # 更新模式按钮选中状态
        self._btn_freeplay.setChecked(not is_countdown)
        self._btn_countdown.setChecked(is_countdown)

        # 显示/隐藏套餐区，同时调整对话框高度（不用 adjustSize，用 setFixedHeight）
        self._countdown_frame.setVisible(is_countdown)
        self.setFixedHeight(
            self._HEIGHT_COUNTDOWN if is_countdown else self._HEIGHT_FREEPLAY
        )

        if not is_countdown:
            self._active_mins = 0
            self._start_btn.setEnabled(True)
            self._start_btn.setText("开始自由计时")
        else:
            self._start_btn.setEnabled(self._active_mins > 0)
            self._start_btn.setText("开始倒计时")

    def _adjust_custom(self, delta: int):
        """加减按钮调整分钟数"""
        try:
            val = int(self._custom_edit.text() or "0")
        except ValueError:
            val = 0
        val = max(1, min(600, val + delta))
        self._custom_edit.setText(str(val))

    def _select_preset(self, mins: int):
        """点击预设按钮"""
        for m, btn in self._preset_btns.items():
            btn.setChecked(m == mins)
        self._custom_edit.blockSignals(True)
        self._custom_edit.setText(str(mins))
        self._custom_edit.blockSignals(False)
        self._set_active_mins(mins)

    def _on_custom_changed(self, text: str):
        """自定义输入框内容变化"""
        # 取消所有预设按钮选中
        for btn in self._preset_btns.values():
            btn.setChecked(False)
        try:
            val = int(text)
            if 1 <= val <= 600:
                self._set_active_mins(val)
        except ValueError:
            pass

    def _set_active_mins(self, mins: int):
        self._active_mins = mins
        h = mins // 60
        m = mins % 60
        if h > 0 and m > 0:
            label = f"{h} 小时 {m} 分钟"
        elif h > 0:
            label = f"{h} 小时"
        else:
            label = f"{m} 分钟"
        self._selected_time_lbl.setText(f"⏱  {label}")
        self._start_btn.setEnabled(True)
        self._start_btn.setText(f"开始 {label} 倒计时")

    def _on_start(self):
        self.note = self._note_input.toPlainText().strip()
        if self.selected_mode == TimerMode.COUNTDOWN:
            self.countdown_minutes = self._active_mins
        else:
            self.countdown_minutes = 0
        self.accept()


# ─────────────────────────────────────────────
# 加时对话框
# ─────────────────────────────────────────────

class AddTimeDialog(QDialog):
    """为倒计时套餐续费加时的对话框"""

    def __init__(self, device_name: str, current_remaining: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"加时 — {device_name}")
        self.setFixedSize(380, 300)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['background']}; }}")
        apply_dark_title_bar(self)

        self.extra_minutes: int = 0
        self._active_mins: int = 0

        self._init_ui(current_remaining)

    def _init_ui(self, current_remaining: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 标题栏 ──
        title_bar = QFrame()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(f"background: {COLORS['countdown']};")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)
        title_lbl = QLabel("⏱  续费加时")
        title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(title_lbl)

        # 剩余时间提示
        from core.billing import format_duration
        rem_text = format_duration(max(0, current_remaining))
        rem_lbl = QLabel(f"剩余 {rem_text}")
        rem_lbl.setStyleSheet("color: #DDD; font-size: 12px;")
        title_layout.addStretch()
        title_layout.addWidget(rem_lbl)
        layout.addWidget(title_bar)

        body = QFrame()
        body.setStyleSheet(f"background: {COLORS['background']};")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        # 快捷时长按钮
        preset_row1 = QHBoxLayout()
        preset_row1.setSpacing(8)
        preset_row2 = QHBoxLayout()
        preset_row2.setSpacing(8)

        self._preset_btns: dict[int, QPushButton] = {}
        for i, mins in enumerate([30, 60, 90, 120, 150, 180]):
            btn = self._make_preset_btn(mins)
            self._preset_btns[mins] = btn
            if i < 3:
                preset_row1.addWidget(btn)
            else:
                preset_row2.addWidget(btn)

        body_layout.addLayout(preset_row1)
        body_layout.addLayout(preset_row2)

        # 自定义时长
        custom_row = QHBoxLayout()
        custom_row.setSpacing(6)

        custom_lbl = QLabel("自定义：")
        custom_lbl.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 13px;")

        self._minus_btn = QPushButton("－")
        self._minus_btn.setFixedSize(32, 32)
        self._minus_btn.setStyleSheet(self._adj_btn_style())
        self._minus_btn.clicked.connect(lambda: self._adjust_custom(-1))

        self._custom_edit = QLineEdit("60")
        self._custom_edit.setValidator(QIntValidator(1, 600))
        self._custom_edit.setFixedSize(58, 32)
        self._custom_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 16px;
                font-weight: bold;
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
            }}
            QLineEdit:focus {{ border-color: {COLORS['countdown']}; }}
        """)
        self._custom_edit.textChanged.connect(self._on_custom_changed)

        self._plus_btn = QPushButton("＋")
        self._plus_btn.setFixedSize(32, 32)
        self._plus_btn.setStyleSheet(self._adj_btn_style())
        self._plus_btn.clicked.connect(lambda: self._adjust_custom(1))

        mins_lbl = QLabel("分钟")
        mins_lbl.setStyleSheet(f"color: {COLORS['text_dark']}; font-size: 13px; font-weight: bold;")

        custom_row.addWidget(custom_lbl)
        custom_row.addStretch()
        custom_row.addWidget(self._minus_btn)
        custom_row.addWidget(self._custom_edit)
        custom_row.addWidget(self._plus_btn)
        custom_row.addWidget(mins_lbl)
        body_layout.addLayout(custom_row)

        # 当前选中显示
        self._selected_lbl = QLabel("未选择")
        self._selected_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._selected_lbl.setStyleSheet(
            f"color: {COLORS['countdown']}; font-size: 20px; font-weight: bold;"
        )
        body_layout.addWidget(self._selected_lbl)

        layout.addWidget(body)

        # ── 按钮区 ──
        btn_bar = QFrame()
        btn_bar.setStyleSheet(
            f"background: {COLORS['card_bg']}; border-top: 1px solid {COLORS['border_soft']};"
        )
        btn_bar_layout = QHBoxLayout(btn_bar)
        btn_bar_layout.setContentsMargins(20, 10, 20, 10)
        btn_bar_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                color: {COLORS['text_dark']};
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['accent']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        self._confirm_btn = QPushButton("＋  确认加时")
        self._confirm_btn.setFixedHeight(38)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['countdown']};
                border: none;
                border-radius: 7px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: {COLORS['countdown']}; }}
            QPushButton:disabled {{ background: {COLORS['border_soft']}; color: #A7B0BE; }}
        """)
        self._confirm_btn.clicked.connect(self._on_confirm)

        btn_bar_layout.addWidget(cancel_btn)
        btn_bar_layout.addStretch()
        btn_bar_layout.addWidget(self._confirm_btn)
        layout.addWidget(btn_bar)

    def _adj_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 16px;
                font-weight: bold;
                color: {COLORS['text_dark']};
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; }}
        """

    def _make_preset_btn(self, mins: int) -> QPushButton:
        h = mins // 60
        m = mins % 60
        if h > 0 and m > 0:
            label = f"{h}小时{m}分"
        elif h > 0:
            label = f"{h}小时"
        else:
            label = f"{m}分钟"
        btn = QPushButton(label)
        btn.setFixedHeight(40)
        btn.setCheckable(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                color: {COLORS['text_dark']};
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background: {COLORS['countdown']};
                border-color: {COLORS['countdown']};
                color: white;
            }}
            QPushButton:hover:!checked {{
                border-color: {COLORS['countdown']};
                color: {COLORS['countdown']};
            }}
        """)
        btn.clicked.connect(lambda checked, m=mins: self._select_preset(m))
        return btn

    def _select_preset(self, mins: int):
        for m, btn in self._preset_btns.items():
            btn.setChecked(m == mins)
        self._custom_edit.blockSignals(True)
        self._custom_edit.setText(str(mins))
        self._custom_edit.blockSignals(False)
        self._set_active_mins(mins)

    def _adjust_custom(self, delta: int):
        try:
            val = int(self._custom_edit.text() or "0")
        except ValueError:
            val = 0
        val = max(1, min(600, val + delta))
        self._custom_edit.setText(str(val))

    def _on_custom_changed(self, text: str):
        for btn in self._preset_btns.values():
            btn.setChecked(False)
        try:
            val = int(text)
            if 1 <= val <= 600:
                self._set_active_mins(val)
        except ValueError:
            pass

    def _set_active_mins(self, mins: int):
        self._active_mins = mins
        h = mins // 60
        m = mins % 60
        if h > 0 and m > 0:
            label = f"{h} 小时 {m} 分钟"
        elif h > 0:
            label = f"{h} 小时"
        else:
            label = f"{m} 分钟"
        self._selected_lbl.setText(f"＋  {label}")
        self._confirm_btn.setEnabled(True)
        self._confirm_btn.setText(f"＋  加 {label}")

    def _on_confirm(self):
        self.extra_minutes = self._active_mins
        self.accept()


# ─────────────────────────────────────────────
# 包厢面板
# ─────────────────────────────────────────────

class DeviceGridWidget(QWidget):
    """接收设备卡片拖放的网格容器。"""

    def __init__(self, panel: "DevicePanel"):
        super().__init__(panel)
        self._panel = panel
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DeviceCard.DRAG_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DeviceCard.DRAG_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        dragged_id = self._panel._device_id_from_mime(event.mimeData())
        if dragged_id is None:
            event.ignore()
            return

        target_id = None
        target = self.childAt(self._panel._event_pos(event))
        while target is not None:
            if isinstance(target, DeviceCard):
                target_id = target.device_id
                break
            target = target.parentWidget()

        if self._panel._handle_device_drop(dragged_id, target_id):
            event.acceptProposedAction()
        else:
            event.ignore()


class DevicePanel(QWidget):
    """
    包厢面板：显示所有包厢卡片，处理开始/暂停/恢复/结束逻辑。

    Signals:
        session_completed(): 有会话完成，通知主窗口刷新统计
    """

    session_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[int, DeviceCard] = {}
        self._all_devices: list = []
        self._summary_labels: dict[str, QLabel] = {}
        self._summary_chips: list[QFrame] = []
        self._insight_labels: dict[str, QLabel] = {}
        self._placeholder_label = None
        self._columns = 1
        self._card_width = 292
        self._grid_spacing = 18
        self._ordered_device_ids: list[int] = []

        self._init_ui()
        self.load_devices()

    # ─────────────────────────────────────────
    # UI 初始化
    # ─────────────────────────────────────────

    def _init_ui(self):
        self.setStyleSheet(f"background: {COLORS['background']};")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 30, 32, 30)
        root.setSpacing(20)

        header = QHBoxLayout()
        header.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        title = QLabel("设备控制台")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {COLORS['text_dark']};"
        )
        subtitle = QLabel("统一查看空闲、进行中、暂停与到时设备，减少窗口跳转。")
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {COLORS['text_muted']};"
        )
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(10)

        self._reload_btn = QPushButton("刷新状态")
        self._reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reload_btn.setFixedHeight(32)
        self._reload_btn.setStyleSheet(self._ghost_button_style())
        self._reload_btn.clicked.connect(self.load_devices)

        actions.addWidget(self._reload_btn)
        header.addLayout(actions)
        root.addLayout(header)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)
        summary_config = [
            ("空闲设备", DeviceStatus.IDLE, COLORS["text_dark"]),
            ("进行中", DeviceStatus.ACTIVE, COLORS["accent"]),
            ("已暂停", DeviceStatus.PAUSED, COLORS["warning"]),
            ("到时提醒", DeviceStatus.EXPIRED, COLORS["danger"]),
        ]
        for title_text, status, color in summary_config:
            chip, value_lbl = self._create_summary_chip(title_text, color)
            self._summary_labels[status] = value_lbl
            self._summary_chips.append(chip)
            summary_row.addWidget(chip, 1)
        root.addLayout(summary_row)

        body = QHBoxLayout()
        body.setSpacing(22)

        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        list_bar = QFrame()
        list_bar.setObjectName("panelCard")
        list_bar.setStyleSheet(self._panel_style())
        list_bar_layout = QHBoxLayout(list_bar)
        list_bar_layout.setContentsMargins(18, 14, 18, 14)
        list_bar_layout.setSpacing(10)

        list_title = QLabel("设备列表 / 拖动卡片调整位置")
        list_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {COLORS['text_dark']};"
        )
        list_bar_layout.addWidget(list_title)
        list_bar_layout.addStretch()

        self._device_total_badge = QLabel("全部 0")
        self._device_total_badge.setStyleSheet(
            f"background: {COLORS['primary']}; color: white; padding: 5px 10px; "
            "border-radius: 5px; font-size: 11px; font-weight: 700;"
        )
        list_bar_layout.addWidget(self._device_total_badge)
        left_col.addWidget(list_bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setCursor(Qt.CursorShape.ArrowCursor)
        self._scroll.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {COLORS['card_bg']};
                width: 12px;
                margin: 3px 2px 3px 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-height: 42px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #2F4358;
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        self._grid_widget = DeviceGridWidget(self)
        self._grid_widget.setCursor(Qt.CursorShape.ArrowCursor)
        self._grid_widget.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 12, 28)
        self._grid_layout.setHorizontalSpacing(self._grid_spacing)
        self._grid_layout.setVerticalSpacing(self._grid_spacing)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._grid_widget)
        left_col.addWidget(self._scroll, 1)
        body.addLayout(left_col, 1)

        root.addLayout(body, 1)

    def _create_summary_chip(self, title: str, color: str):
        chip = QFrame()
        chip.setObjectName("panelCard")
        chip.setStyleSheet(self._panel_style())
        chip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        chip.setFixedHeight(68)
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(title_lbl)

        value_lbl = QLabel("0")
        value_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 700;")
        layout.addWidget(value_lbl)
        layout.addStretch()

        return chip, value_lbl

    def _clear_grid_layout(self, delete_widgets: bool = False):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if not widget:
                continue
            if delete_widgets:
                if widget is self._placeholder_label:
                    self._placeholder_label = None
                widget.deleteLater()
            else:
                widget.hide()

    def _show_placeholder(self, text: str):
        if self._placeholder_label is None:
            self._placeholder_label = QLabel()
            self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._placeholder_label.setStyleSheet(
                f"background: {COLORS['card_bg']}; border: 1px solid {COLORS['border']}; "
                "border-radius: 8px; "
                f"color: {COLORS['text_muted']}; font-size: 14px; padding: 40px;"
            )
        self._placeholder_label.setText(text)
        self._placeholder_label.show()
        self._grid_layout.addWidget(
            self._placeholder_label, 0, 0, 1, max(1, self._columns)
        )

    def _update_summary_chips(self, cards):
        counts = {status: 0 for status in self._summary_labels}
        for card in cards:
            counts[card._status] = counts.get(card._status, 0) + 1
        for status, lbl in self._summary_labels.items():
            lbl.setText(str(counts.get(status, 0)))

    @staticmethod
    def _columns_for_width(width: int, card_width: int, spacing: int) -> int:
        return max(1, (max(0, width) + spacing) // (card_width + spacing))

    @staticmethod
    def _move_device_id(device_ids: list[int], dragged_id: int, target_id: int | None) -> list[int]:
        if dragged_id not in device_ids or dragged_id == target_id:
            return list(device_ids)
        ordered = [device_id for device_id in device_ids if device_id != dragged_id]
        if target_id is None or target_id not in ordered:
            ordered.append(dragged_id)
            return ordered
        target_index = ordered.index(target_id)
        ordered.insert(target_index, dragged_id)
        return ordered

    def _event_pos(self, event):
        if hasattr(event, "position"):
            return event.position().toPoint()
        return event.pos()

    def _device_id_from_mime(self, mime_data) -> int | None:
        if not mime_data.hasFormat(DeviceCard.DRAG_MIME_TYPE):
            return None
        try:
            return int(bytes(mime_data.data(DeviceCard.DRAG_MIME_TYPE)).decode("utf-8"))
        except (TypeError, ValueError):
            return None

    def _calculate_columns(self) -> int:
        if not hasattr(self, "_scroll"):
            return self._columns
        width = self._scroll.viewport().width()
        return self._columns_for_width(width, self._card_width, self._grid_spacing)

    def _ordered_cards(self) -> list[DeviceCard]:
        ordered_ids = [device_id for device_id in self._ordered_device_ids if device_id in self._cards]
        missing_ids = [device_id for device_id in self._cards if device_id not in ordered_ids]
        self._ordered_device_ids = ordered_ids + missing_ids
        return [self._cards[device_id] for device_id in self._ordered_device_ids]

    def _handle_device_drop(self, dragged_id: int, target_id: int | None) -> bool:
        new_order = self._move_device_id(self._ordered_device_ids, dragged_id, target_id)
        if new_order == self._ordered_device_ids:
            return False

        self._ordered_device_ids = new_order
        self._apply_filters()
        if not db.update_device_sort_order(self._ordered_device_ids):
            show_warning(self, "保存排序失败", "包厢顺序保存失败，重启后可能恢复为旧顺序。")
        return True

    def _relayout_cards_if_needed(self):
        new_columns = self._calculate_columns()
        if new_columns != self._columns:
            self._columns = new_columns
            self._apply_filters()

    def _apply_filters(self, *args):
        cards = self._ordered_cards()
        if not cards:
            if not self._all_devices:
                self.refresh_dashboard()
                return
            self._clear_grid_layout(delete_widgets=False)
            self._show_placeholder("暂无包厢，您可以在「设置」里添加新的设备")
            self.refresh_dashboard()
            return

        self._clear_grid_layout(delete_widgets=False)
        self._columns = self._calculate_columns()
        columns = max(1, self._columns)
        for idx, card in enumerate(cards):
            row, col = divmod(idx, columns)
            self._grid_layout.addWidget(card, row, col)
            card.show()
        self.refresh_dashboard()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._relayout_cards_if_needed)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._relayout_cards_if_needed)

    # ─────────────────────────────────────────
    # 加载包厢
    # ─────────────────────────────────────────

    def load_devices(self):
        """从数据库加载所有包厢，创建对应的卡片"""
        for card in self._cards.values():
            card.timer.reset()
            card.deleteLater()
        self._cards.clear()

        self._clear_grid_layout(delete_widgets=True)

        self._all_devices = list(db.get_all_devices())
        self._ordered_device_ids = [device["id"] for device in self._all_devices]

        if not self._all_devices:
            self._show_placeholder("暂无包厢，您可以在「设置」里添加新的设备")
            return

        for device in self._all_devices:
            card = DeviceCard(
                device_id=device["id"],
                device_name=device["name"],
                type_name=device["type_name"],
                status=device["status"],
                parent=self._grid_widget,
            )
            card.checkout_requested.connect(self._on_checkout_requested)
            card.add_time_requested.connect(self._on_add_time)
            card.status_changed.connect(lambda *_: self.refresh_dashboard())

            # 直接连接开始/暂停/继续按钮（DeviceCard 中未预先连接，无需 disconnect）
            card.start_btn.clicked.connect(
                lambda checked, d=device["id"]: self._on_start(d)
            )
            card.pause_btn.clicked.connect(
                lambda checked, d=device["id"]: self._on_pause(d)
            )
            card.resume_btn.clicked.connect(
                lambda checked, d=device["id"]: self._on_resume(d)
            )
            card.set_density_mode("comfortable")
            self._cards[device["id"]] = card

        self._restore_active_sessions()
        self._apply_filters()

    def _restore_active_sessions(self):
        """程序启动时恢复所有未结束的会话"""
        active_sessions = db.get_all_active_sessions()
        for session in active_sessions:
            device_id = session["device_id"]
            card = self._cards.get(device_id)
            if card is None:
                continue

            start_time = datetime.strptime(
                session["start_time"], "%Y-%m-%d %H:%M:%S"
            )
            pause_duration    = session["pause_duration"] or 0
            is_paused         = session["status"] == SessionStatus.PAUSED
            mode              = session["timer_mode"] or TimerMode.FREEPLAY
            countdown_seconds = session["countdown_seconds"] or 0

            # 判断是否已超时（countdown 模式）
            from core.timer_engine import TimerEngine
            tmp = TimerEngine(device_id, mode=mode,
                              countdown_seconds=countdown_seconds)
            tmp.start_time = start_time
            tmp.pause_duration = pause_duration
            elapsed = tmp.get_elapsed_seconds()
            is_expired = (mode == TimerMode.COUNTDOWN
                          and elapsed >= countdown_seconds
                          and countdown_seconds > 0)

            card.restore_session(
                session_id=session["id"],
                mode=mode,
                countdown_seconds=countdown_seconds,
                start_time=start_time,
                pause_duration=pause_duration,
                is_paused=is_paused,
                is_expired=is_expired,
                note=session["note"] or "",
            )

    # ─────────────────────────────────────────
    # 包厢操作
    # ─────────────────────────────────────────

    def _on_start(self, device_id: int):
        """弹出模式选择对话框，然后开始计时"""
        card = self._cards.get(device_id)
        if card is None:
            return

        dialog = StartTimerDialog(card.device_name, parent=self)
        if not dialog.exec():
            self._refresh_cursor_after_action()
            return

        mode = dialog.selected_mode
        countdown_seconds = dialog.countdown_minutes * 60

        session_id = db.start_session(
            device_id=device_id,
            timer_mode=mode,
            countdown_seconds=countdown_seconds,
            note=dialog.note,
        )
        card.start_timer(
            session_id=session_id,
            mode=mode,
            countdown_seconds=countdown_seconds,
            note=dialog.note,
        )
        self.refresh_dashboard()
        self._refresh_cursor_after_action()

    def _refresh_cursor_after_action(self):
        QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
        QTimer.singleShot(0, QApplication.restoreOverrideCursor)

    def _on_pause(self, device_id: int):
        """暂停计时"""
        card = self._cards.get(device_id)
        if card is None:
            return
        session_id = card.current_session_id
        if session_id < 0:
            return
        db.pause_session(session_id, device_id)
        card.pause_timer()
        self.refresh_dashboard()

    def _on_resume(self, device_id: int):
        """恢复计时"""
        card = self._cards.get(device_id)
        if card is None:
            return
        session_id = card.current_session_id
        if session_id < 0:
            return
        db.resume_session(session_id, device_id)
        session = db.get_active_session(device_id)
        pause_duration = session["pause_duration"] if session else 0
        card.resume_timer(pause_duration)
        self.refresh_dashboard()

    def _on_add_time(self, device_id: int):
        """弹出加时对话框，为倒计时套餐续费"""
        card = self._cards.get(device_id)
        if card is None:
            return
        session_id = card.current_session_id
        if session_id < 0:
            return

        remaining = card.timer.get_remaining_seconds()
        dialog = AddTimeDialog(card.device_name, remaining, parent=self)
        if not dialog.exec():
            self._refresh_cursor_after_action()
            return

        extra_seconds = dialog.extra_minutes * 60
        card.add_time(extra_seconds)
        new_total = card.timer.countdown_seconds
        db.extend_session_countdown(session_id, new_total)
        self.refresh_dashboard()
        self._refresh_cursor_after_action()

    def _on_checkout_requested(self, device_id: int):
        """处理结束请求"""
        card = self._cards.get(device_id)
        if card is None:
            return

        session_id = card.current_session_id
        if session_id < 0:
            show_warning(self, "错误", "未找到进行中的会话！")
            return

        session = db.get_active_session(device_id)
        if session is None:
            return

        # 弹出对话框前先冻结计时（停止 QTimer，但不改变状态），
        # 取消时恢复，确认时正式结束
        card.timer._timer.stop()
        elapsed = card.current_elapsed   # 冻结后读取，保证显示与保存一致

        dialog = CheckoutDialog(
            device_name=card.device_name,
            type_name=card.type_name,
            timer_mode=card.timer.mode,
            start_time=session["start_time"],
            elapsed_seconds=elapsed,
            countdown_seconds=session["countdown_seconds"] or 0,
            initial_note=session["note"] or "",
            parent=self,
        )

        if dialog.exec():
            # 确认结束：正式停止并保存
            final_elapsed = card.stop_timer()
            success = db.end_session(
                session_id=session_id,
                device_id=device_id,
                total_seconds=final_elapsed,
                paid=dialog.paid,
                note=dialog.note,
                payment_method=dialog.payment_method,
            )
            if success:
                self.refresh_dashboard()
                self.session_completed.emit()
            else:
                show_critical(self, "错误", "数据保存失败，请重试！")
        else:
            # 取消：恢复计时（仅当计时引擎仍在运行状态时）
            if card.timer._is_running and not card.timer._is_paused:
                card.timer._timer.start()
        self._refresh_cursor_after_action()

    # ─────────────────────────────────────────
    # 统计信息
    # ─────────────────────────────────────────

    def get_status_counts(self) -> dict:
        """返回各状态包厢数量"""
        counts = {
            DeviceStatus.IDLE:        0,
            DeviceStatus.ACTIVE:      0,
            DeviceStatus.PAUSED:      0,
            DeviceStatus.EXPIRED:     0,
            DeviceStatus.MAINTENANCE: 0,
        }
        for card in self._cards.values():
            counts[card._status] = counts.get(card._status, 0) + 1
        return counts

    def refresh_dashboard(self):
        counts = self.get_status_counts()
        total = len(self._cards)

        self._device_total_badge.setText(f"全部 {total}")
        self._update_summary_chips(list(self._cards.values()))

    def _panel_style(self) -> str:
        return f"""
            QFrame#panelCard {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame#panelCard QLabel {{
                background: transparent;
                border: none;
            }}
        """

    def _ghost_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: {COLORS['accent']};
                color: {COLORS['accent']};
                background: {COLORS['card_bg']};
            }}
        """

    def _solid_button_style(self, color: str) -> str:
        text_color = COLORS["accent_text"] if color == COLORS["accent"] else "white"
        return f"""
            QPushButton {{
                background: {color};
                color: {text_color};
                border: none;
                border-radius: 7px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {color};
            }}
        """
