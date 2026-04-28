"""Dark themed modal message dialogs used across the app."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from config import COLORS, is_dark_theme
from ui.window_chrome import apply_dark_title_bar


_TONE_STYLES = {
    "information": {
        "text": "i",
        "color": COLORS["accent"],
        "background": "#102830",
        "border": "#27545D",
    },
    "warning": {
        "text": "!",
        "color": COLORS["warning"],
        "background": "#2B2313",
        "border": "#7C5816",
    },
    "critical": {
        "text": "!",
        "color": COLORS["danger"],
        "background": "#2A1721",
        "border": "#563041",
    },
}


def make_message_dialog(parent, title: str, message: str, tone: str = "information") -> QDialog:
    """Create a styled message dialog without executing it."""
    tone_style = _TONE_STYLES.get(tone, _TONE_STYLES["information"])

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setMinimumWidth(390)
    dialog.setStyleSheet(_dialog_style())
    apply_dark_title_bar(dialog)

    root = QVBoxLayout(dialog)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(0)

    card = QFrame()
    card.setObjectName("messageCard")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(20, 20, 20, 18)
    card_layout.setSpacing(16)

    content = QHBoxLayout()
    content.setSpacing(14)
    content.setAlignment(Qt.AlignmentFlag.AlignTop)

    icon_label = QLabel(tone_style["text"])
    icon_label.setObjectName("messageToneIcon")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setFixedSize(36, 36)
    icon_label.setStyleSheet(
        f"""
        QLabel#messageToneIcon {{
            background: {tone_style['background']};
            color: {tone_style['color']};
            border: 1px solid {tone_style['border']};
            border-radius: 18px;
            font-size: 22px;
            font-weight: 900;
        }}
        """
    )
    content.addWidget(icon_label)

    text_col = QVBoxLayout()
    text_col.setSpacing(8)

    title_label = QLabel(title)
    title_label.setObjectName("messageTitle")
    title_label.setStyleSheet(
        f"color: {COLORS['text_dark']}; font-size: 20px; font-weight: 900;"
    )
    text_col.addWidget(title_label)

    message_label = QLabel(message)
    message_label.setObjectName("messageBody")
    message_label.setWordWrap(True)
    message_label.setMinimumWidth(250)
    body_color = "#DCE8F2" if is_dark_theme() else COLORS["text_muted"]
    message_label.setStyleSheet(f"color: {body_color}; font-size: 14px;")
    text_col.addWidget(message_label)

    content.addLayout(text_col, 1)
    card_layout.addLayout(content)

    actions = QHBoxLayout()
    actions.addStretch()
    ok_btn = QPushButton("确定")
    ok_btn.setObjectName("messageOkButton")
    ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    ok_btn.setFixedHeight(36)
    ok_btn.setMinimumWidth(86)
    ok_btn.setStyleSheet(_primary_button_style())
    ok_btn.clicked.connect(dialog.accept)
    actions.addWidget(ok_btn)
    card_layout.addLayout(actions)

    root.addWidget(card)
    return dialog


def show_information(parent, title: str, message: str):
    return _show_message(parent, title, message, "information")


def show_warning(parent, title: str, message: str):
    return _show_message(parent, title, message, "warning")


def show_critical(parent, title: str, message: str):
    return _show_message(parent, title, message, "critical")


def _show_message(parent, title: str, message: str, tone: str):
    dialog = make_message_dialog(parent, title, message, tone)
    try:
        return dialog.exec()
    finally:
        dialog.deleteLater()


def _dialog_style() -> str:
    return f"""
        QDialog {{
            background: {COLORS['background']};
        }}
        QFrame#messageCard {{
            background: {COLORS['card_bg']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
        }}
        QLabel {{
            background: transparent;
            border: none;
        }}
    """


def _primary_button_style() -> str:
    return f"""
        QPushButton {{
            background: {COLORS['accent']};
            color: {COLORS['accent_text']};
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 900;
            padding: 0 16px;
        }}
        QPushButton:hover {{
            background: #A7FBFF;
        }}
        QPushButton:pressed {{
            background: #5DE8F0;
        }}
    """
