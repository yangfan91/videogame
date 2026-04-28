"""
结束确认对话框（v2）
显示使用时长，提供付款状态标记、收款方式（多选）和备注输入。
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QCheckBox,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon, QPainter, QPixmap

from core.billing import format_duration, format_duration_readable
from config import ASSETS_DIR, COLORS, TimerMode
from ui.window_chrome import apply_dark_title_bar


CHECKBOX_CHECK_ICON = Path(ASSETS_DIR, "checkbox_checked.svg").as_posix()
BUTTON_CHECK_ICON = Path(ASSETS_DIR, "button_check.svg").as_posix()

# 可选收款方式
PAYMENT_METHODS = [
    {"key": "美团",  "icon": "🟡", "color": "#F5A623"},
    {"key": "抖音",  "icon": "⚫", "color": "#161823"},
    {"key": "现金",  "icon": "💵", "color": "#27AE60"},
]


class CheckoutDialog(QDialog):
    """
    结束确认对话框。

    Args:
        device_name:      包厢名称
        type_name:        包厢类型
        timer_mode:       计时模式（countdown / freeplay）
        start_time:       开始时间字符串
        elapsed_seconds:  实际使用秒数
        countdown_seconds: 套餐总秒数（countdown 模式）
        parent:           父窗口

    Results (after accept):
        paid:           bool
        payment_method: str  逗号分隔，如 "美团,现金"
        note:           str
    """

    def __init__(self, device_name: str, type_name: str,
                 timer_mode: str, start_time: str,
                 elapsed_seconds: int,
                 countdown_seconds: int = 0,
                 initial_note: str = "",
                 parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.type_name = type_name
        self.timer_mode = timer_mode
        self.start_time = start_time
        self.elapsed_seconds = elapsed_seconds
        self.countdown_seconds = countdown_seconds
        self.initial_note = initial_note

        # 结果（确认后填充）
        self.paid: bool = False
        self.payment_method: str = ""
        self.note: str = ""

        self._init_ui()
        apply_dark_title_bar(self)

    def _init_ui(self):
        self.setWindowTitle(f"结束 - {self.device_name}")
        self.setFixedWidth(460)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['background']}; }}
            QLabel {{ color: {COLORS['text_dark']}; font-size: 13px; }}
            QTextEdit {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 8px;
                font-size: 13px;
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
            }}
            QTextEdit:focus {{ border-color: {COLORS['accent']}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── 标题栏 ──
        title_bar = QFrame()
        title_bar.setStyleSheet(f"background-color: {COLORS['primary']};")
        title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)
        mode_icon  = "⏱️" if self.timer_mode == TimerMode.COUNTDOWN else "🎮"
        mode_label = TimerMode.LABELS.get(self.timer_mode, "")
        title_label = QLabel(
            f"{mode_icon}  结束 — {self.device_name}（{self.type_name}）· {mode_label}"
        )
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        title_layout.addWidget(title_label)
        layout.addWidget(title_bar)

        # ── 信息区 ──
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background: {COLORS['card_bg']};")
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setVerticalSpacing(10)
        info_layout.setHorizontalSpacing(12)

        def add_row(row, label_text, value_text, value_color=None, value_bold=False):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
            val = QLabel(value_text)
            style = f"font-size: 13px; color: {value_color or COLORS['text_dark']};"
            if value_bold:
                style += " font-weight: bold;"
            val.setStyleSheet(style)
            info_layout.addWidget(lbl, row, 0)
            info_layout.addWidget(val, row, 1)

        add_row(0, "开始时间：", self.start_time)
        add_row(1, "实际时长：",
                format_duration_readable(self.elapsed_seconds),
                value_color=COLORS['accent'], value_bold=True)
        add_row(2, "计时时长：", format_duration(self.elapsed_seconds))

        if self.timer_mode == TimerMode.COUNTDOWN:
            overtime = self.elapsed_seconds - self.countdown_seconds
            add_row(3, "套餐时长：", format_duration(self.countdown_seconds))
            if overtime > 0:
                add_row(4, "超时时长：",
                        format_duration_readable(overtime),
                        value_color=COLORS['danger'], value_bold=True)
            else:
                add_row(4, "剩余时长：",
                        format_duration_readable(abs(overtime)),
                        value_color=COLORS['success'])

        layout.addWidget(info_frame)

        # ── 输入区 ──
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background: {COLORS['background']};")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 14, 20, 14)
        input_layout.setSpacing(12)

        # 付款状态复选框
        self.paid_checkbox = QCheckBox("已付款（勾选表示客户已完成付款）")
        self.paid_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_dark']};
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
            }}
            QCheckBox::indicator:checked {{
                background: {COLORS['surface']};
                border: 2px solid {COLORS['success']};
                border-radius: 4px;
                image: url({CHECKBOX_CHECK_ICON});
            }}
            QCheckBox::indicator:unchecked {{
                background: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                image: none;
            }}
        """)
        self.paid_checkbox.toggled.connect(self._on_paid_toggled)
        input_layout.addWidget(self.paid_checkbox)

        # ── 收款方式区（常驻，未付款时禁用） ──
        self._payment_frame = QFrame()
        self._payment_frame.setObjectName("paymentPanel")
        self._payment_frame.setStyleSheet(f"""
            QFrame#paymentPanel {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        pm_layout = QVBoxLayout(self._payment_frame)
        pm_layout.setContentsMargins(10, 10, 10, 10)
        pm_layout.setSpacing(8)

        pm_title = QLabel("收款方式（可多选）：")
        pm_title.setStyleSheet(self._form_label_style())
        pm_layout.addWidget(pm_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._payment_btns: dict[str, QPushButton] = {}
        for pm in PAYMENT_METHODS:
            btn = self._make_payment_btn(pm["key"], pm["icon"])
            self._payment_btns[pm["key"]] = btn
            btn.setEnabled(False)   # 默认禁用，勾选已付款后启用
            btn_row.addWidget(btn)

        pm_layout.addLayout(btn_row)
        input_layout.addWidget(self._payment_frame)

        # 备注
        note_label = QLabel("备注（可选）：")
        note_label.setStyleSheet(self._form_label_style())
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("如：买了2小时券、赠送30分钟等")
        self.note_input.setFixedHeight(56)
        self.note_input.setPlainText(self.initial_note)
        input_layout.addWidget(note_label)
        input_layout.addWidget(self.note_input)

        layout.addWidget(input_frame)

        # ── 按钮区 ──
        btn_frame = QFrame()
        btn_frame.setStyleSheet(
            f"background: {COLORS['card_bg']}; border-top: 1px solid {COLORS['border_soft']};"
        )
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(20, 12, 20, 12)
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(38)
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

        confirm_btn = QPushButton("确认结束")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(38)
        confirm_btn.setIcon(QIcon(BUTTON_CHECK_ICON))
        confirm_btn.setIconSize(QSize(18, 18))
        confirm_btn.setProperty("usesVectorConfirmIcon", True)
        confirm_btn.setStyleSheet(self._confirm_btn_style())
        confirm_btn.clicked.connect(self._on_confirm)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(confirm_btn)
        layout.addWidget(btn_frame)

    # ─────────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────────

    def _form_label_style(self) -> str:
        return (
            f"color: {COLORS['text_dark']}; font-size: 13px; "
            "background: transparent; border: none;"
        )

    def _confirm_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['accent']};
                border: none;
                border-radius: 7px;
                color: {COLORS['accent_text']};
                font-size: 13px;
                font-weight: bold;
                padding: 0 20px;
            }}
            QPushButton:hover:!disabled {{
                background: #A7FBFF;
            }}
            QPushButton:pressed:!disabled {{
                background: #5DE8F0;
            }}
        """

    def _payment_icon(self, icon: str) -> QIcon:
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = QFont("Segoe UI Emoji")
        font.setPixelSize(30)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, icon)
        painter.end()
        return QIcon(pixmap)

    def _make_payment_btn(self, key: str, icon: str) -> QPushButton:
        btn = QPushButton(key)
        btn.setIcon(self._payment_icon(icon))
        btn.setIconSize(QSize(34, 34))
        btn.setProperty("paymentIconCanvasSize", 48)
        btn.setCheckable(True)
        btn.setFixedHeight(50)
        btn.setMinimumWidth(128)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                color: {COLORS['text_dark']};
                font-size: 14px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:checked {{
                background: {COLORS['success']}22;
                border: 2px solid {COLORS['success']};
                color: {COLORS['success']};
            }}
            QPushButton:hover:!checked:!disabled {{
                border-color: {COLORS['success']};
                background: {COLORS['success']}11;
            }}
            QPushButton:disabled {{
                background: {COLORS['surface_alt']};
                border-color: {COLORS['border_soft']};
                color: #A7B0BE;
            }}
        """)
        return btn

    def _on_paid_toggled(self, checked: bool):
        for btn in self._payment_btns.values():
            btn.setEnabled(checked)
            if not checked:
                btn.setChecked(False)

    # ─────────────────────────────────────────
    # 槽
    # ─────────────────────────────────────────

    def _on_confirm(self):
        """确认结束"""
        self.paid = self.paid_checkbox.isChecked()
        selected = [key for key, btn in self._payment_btns.items() if btn.isChecked()]
        self.payment_method = ",".join(selected)
        self.note = self.note_input.toPlainText().strip()
        self.accept()
