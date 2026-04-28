"""
主窗口。
采用侧边导航 + 内容区的控制台布局。
"""
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config
from config import APP_ICON_PATH, APP_NAME, APP_VERSION, COLORS, NAV_ICON_PATHS
from ui.device_panel import DevicePanel
from ui.settings_dialog import SettingsPanel
from ui.stats_panel import StatsPanel
from ui.window_chrome import apply_dark_title_bar


class MainWindow(QMainWindow):
    """应用主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        app_icon = QIcon(APP_ICON_PATH)
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setMinimumSize(1160, 760)
        self.resize(1360, 860)
        config.set_theme(config.CURRENT_THEME)
        self._init_ui()
        apply_dark_title_bar(self)

    def _init_ui(self):
        self.setStyleSheet(f"QMainWindow {{ background: {COLORS['background']}; }}")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        central = QWidget()
        central.setCursor(Qt.CursorShape.ArrowCursor)
        self._central = central
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self._stack.setCursor(Qt.CursorShape.ArrowCursor)
        self._stack.setStyleSheet(f"background: {COLORS['background']}; border: none;")

        self._device_panel = DevicePanel()
        self._stats_panel = StatsPanel()
        self._settings_panel = SettingsPanel()
        self._device_panel.session_completed.connect(self._stats_panel.refresh)
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

        self._stack.addWidget(self._device_panel)
        self._stack.addWidget(self._stats_panel)
        self._stack.addWidget(self._settings_panel)
        root.addWidget(self._stack, 1)

        self._switch_page(0)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("linearSidebar")
        sidebar.setFixedWidth(216)
        sidebar.setCursor(Qt.CursorShape.ArrowCursor)
        sidebar.setStyleSheet(
            f"""
            QFrame#linearSidebar {{
                background: {COLORS['sidebar']};
                border: none;
                border-right: 1px solid {COLORS['border_soft']};
            }}
            """
        )
        self._sidebar = sidebar

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(0)

        brand = QLabel("江城电玩")
        brand.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 22px; font-weight: 900; letter-spacing: 0;"
        )
        layout.addWidget(brand)
        layout.addSpacing(30)

        self._nav_device_btn = self._make_nav_btn("控制台", True, NAV_ICON_PATHS["device"])
        self._nav_stats_btn = self._make_nav_btn("统计报表", False, NAV_ICON_PATHS["stats"])
        self._nav_settings_btn = self._make_nav_btn("系统设置", False, NAV_ICON_PATHS["settings"])

        self._nav_device_btn.clicked.connect(lambda: self._switch_page(0))
        self._nav_stats_btn.clicked.connect(lambda: self._switch_page(1))
        self._nav_settings_btn.clicked.connect(lambda: self._switch_page(2))

        layout.addWidget(self._nav_device_btn)
        layout.addSpacing(10)
        layout.addWidget(self._nav_stats_btn)
        layout.addSpacing(10)
        layout.addWidget(self._nav_settings_btn)
        layout.addStretch()

        self._theme_toggle_btn = self._make_theme_toggle_btn()
        self._theme_toggle_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_toggle_btn)
        layout.addSpacing(12)

        footer_dot = QLabel("● 本机在线")
        footer_dot.setStyleSheet(
            f"color: {COLORS['sidebar_muted']}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(footer_dot)
        return sidebar

    def _make_nav_btn(self, text: str, active: bool, icon_path: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(48)
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(26, 26))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._apply_nav_btn_style(btn, active)
        return btn

    def _make_theme_toggle_btn(self) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._apply_theme_toggle_style(btn)
        return btn

    def _apply_theme_toggle_style(self, btn: QPushButton):
        next_theme = "light" if config.CURRENT_THEME == "dark" else "dark"
        btn.setText(f"切换到{config.THEME_LABELS[next_theme]}")
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 800;
                padding: 0 14px;
                text-align: center;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                border-color: {COLORS['accent']};
                background: {COLORS['card_bg']};
            }}
            """
        )

    def _apply_nav_btn_style(self, btn: QPushButton, active: bool):
        if active:
            bg = COLORS["surface_alt"]
            border = COLORS["accent"]
            text = COLORS["text_dark"]
        else:
            bg = COLORS["sidebar"]
            border = COLORS["sidebar"]
            text = COLORS["sidebar_muted"]
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 16px;
                text-align: left;
            }}
            QPushButton:hover {{
                color: {COLORS['text_dark']};
                border-color: {COLORS['accent']};
                background: {COLORS['surface_alt']};
            }}
            """
        )

    def _toggle_theme(self):
        current_index = self._stack.currentIndex()
        self._stop_device_timers()
        config.toggle_theme()
        old_central = self.takeCentralWidget()
        if old_central is not None:
            old_central.deleteLater()
        self._init_ui()
        apply_dark_title_bar(self)
        self._switch_page(current_index)

    def _stop_device_timers(self):
        device_panel = getattr(self, "_device_panel", None)
        if device_panel is None:
            return
        for card in device_panel._cards.values():
            card.timer._timer.stop()
            card._blink_timer.stop()

    def _switch_page(self, index: int):
        self._stack.setCurrentIndex(index)
        self._apply_nav_btn_style(self._nav_device_btn, index == 0)
        self._apply_nav_btn_style(self._nav_stats_btn, index == 1)
        self._apply_nav_btn_style(self._nav_settings_btn, index == 2)
        if index == 1:
            self._stats_panel.refresh()
        elif index == 2:
            self._settings_panel.refresh()
        else:
            self._device_panel.refresh_dashboard()

    def _on_settings_changed(self):
        self._device_panel.load_devices()
        self._stats_panel.refresh()

    def closeEvent(self, event):
        self._stop_device_timers()
        event.accept()
