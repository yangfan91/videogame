import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from config import COLORS, DeviceStatus, TimerMode
from ui.checkout_dialog import CheckoutDialog
from ui.device_card import DeviceCard
from ui.device_panel import DevicePanel
from ui.main_window import MainWindow
from ui.stats_panel import StatsPanel


class DesktopThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_tokens_use_dark_command_center_palette(self):
        self.assertEqual(COLORS["background"], "#0B1118")
        self.assertEqual(COLORS["primary"], "#0F172A")
        self.assertEqual(COLORS["accent"], "#80F7FF")
        self.assertEqual(COLORS["accent_text"], "#08212A")
        self.assertEqual(COLORS["surface"], "#101822")
        self.assertEqual(COLORS["surface_alt"], "#17212C")
        self.assertEqual(COLORS["card_bg"], "#111821")
        self.assertEqual(COLORS["border"], "#243040")
        self.assertEqual(COLORS["border_soft"], "#17212C")
        self.assertEqual(COLORS["sidebar"], "#080D13")
        self.assertEqual(COLORS["text_dark"], "#F8FBFF")
        self.assertEqual(COLORS["text_muted"], "#8A94A6")
        self.assertEqual(COLORS["countdown"], "#8B5CF6")

    def test_native_window_chrome_uses_main_dark_palette(self):
        window = MainWindow()
        checkout = CheckoutDialog(
            device_name="Room 1",
            type_name="VIP",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-28 10:00:00",
            elapsed_seconds=3600,
        )
        try:
            for top_level_window in (window, checkout):
                self.assertIs(top_level_window.property("usesDarkTitleBar"), True)
                self.assertEqual(
                    top_level_window.property("titleBarBackgroundColor"),
                    COLORS["background"],
                )
                self.assertEqual(
                    top_level_window.property("titleBarTextColor"),
                    COLORS["text_dark"],
                )
                self.assertEqual(
                    top_level_window.property("titleBarBorderColor"),
                    COLORS["border"],
                )
        finally:
            checkout.close()
            checkout.deleteLater()
            window.close()
            window.deleteLater()

    def test_main_window_uses_wide_linear_sidebar_with_named_navigation(self):
        window = MainWindow()
        try:
            self.assertEqual(window._sidebar.width(), 216)
            self.assertEqual(window._nav_device_btn.text(), "控制台")
            self.assertEqual(window._nav_stats_btn.text(), "统计报表")
            self.assertEqual(window._nav_settings_btn.text(), "系统设置")
            self.assertIn(COLORS["sidebar"], window._sidebar.styleSheet())
            self.assertIn(COLORS["accent"], window._nav_device_btn.styleSheet())
        finally:
            window.close()
            window.deleteLater()

    def test_device_card_uses_shared_surface_tokens_and_accent_action(self):
        card = DeviceCard(
            device_id=1,
            device_name="小包1",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        try:
            self.assertIn(COLORS["card_bg"], card._card_frame_styles["base"])
            self.assertIn(COLORS["border"], card._card_frame_styles["base"])
            self.assertIn("border-radius: 8px", card._card_frame_styles["base"])
            self.assertIn(COLORS["surface"], card._timer_frame.styleSheet())
            self.assertIn(COLORS["accent"], card.start_btn.styleSheet())
            self.assertIn(f"color: {COLORS['accent_text']}", card.start_btn.styleSheet())
        finally:
            card.deleteLater()

    def test_panel_helpers_use_shared_linear_surfaces(self):
        panel = DevicePanel.__new__(DevicePanel)

        self.assertIn(COLORS["card_bg"], DevicePanel._panel_style(panel))
        self.assertIn(COLORS["border"], DevicePanel._panel_style(panel))
        self.assertIn("border-radius: 8px", DevicePanel._panel_style(panel))
        self.assertIn(COLORS["surface"], DevicePanel._ghost_button_style(panel))
        self.assertIn(COLORS["accent"], DevicePanel._solid_button_style(panel, COLORS["accent"]))
        self.assertIn(
            f"color: {COLORS['accent_text']}",
            DevicePanel._solid_button_style(panel, COLORS["accent"]),
        )

    def test_accent_blue_buttons_use_dark_text_for_readability(self):
        panel = DevicePanel.__new__(DevicePanel)
        stats_panel = StatsPanel.__new__(StatsPanel)
        checkout = CheckoutDialog(
            device_name="小包1",
            type_name="小包",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-27 10:00:00",
            elapsed_seconds=3600,
        )
        try:
            self.assertIn(
                f"color: {COLORS['accent_text']}",
                DevicePanel._solid_button_style(panel, COLORS["accent"]),
            )
            self.assertIn(
                f"color: {COLORS['accent_text']}",
                StatsPanel._solid_button_style(stats_panel, COLORS["accent"]),
            )
            self.assertIn(f"color: {COLORS['accent_text']}", checkout._confirm_btn_style())
        finally:
            checkout.deleteLater()

    def test_checkout_payment_title_matches_note_label_without_fill(self):
        checkout = CheckoutDialog(
            device_name="小包1",
            type_name="小包",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-28 11:48:49",
            elapsed_seconds=3600,
        )
        try:
            labels = {label.text(): label for label in checkout.findChildren(QLabel)}
            payment_title_style = labels["收款方式（可多选）："].styleSheet()
            note_title_style = labels["备注（可选）："].styleSheet()

            self.assertIn(f"color: {COLORS['text_dark']}", payment_title_style)
            self.assertIn("font-size: 13px", payment_title_style)
            self.assertIn("background: transparent", payment_title_style)
            self.assertIn("border: none", payment_title_style)
            self.assertEqual(payment_title_style, note_title_style)
        finally:
            checkout.deleteLater()

    def test_checkout_payment_buttons_reserve_room_for_icons(self):
        checkout = CheckoutDialog(
            device_name="小包1",
            type_name="小包",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-28 11:48:49",
            elapsed_seconds=3600,
        )
        try:
            self.assertEqual(checkout.width(), 460)
            self.assertEqual(set(checkout._payment_btns), {"美团", "抖音", "现金"})
            for key, button in checkout._payment_btns.items():
                self.assertEqual(button.text(), key)
                self.assertFalse(button.icon().isNull())
                self.assertGreaterEqual(button.iconSize().width(), 34)
                self.assertGreaterEqual(button.iconSize().height(), 34)
                self.assertEqual(button.property("paymentIconCanvasSize"), 48)
                self.assertGreaterEqual(button.minimumWidth(), 128)
                self.assertEqual(button.minimumHeight(), 50)
                self.assertIn("padding: 0 16px", button.styleSheet())
        finally:
            checkout.deleteLater()

    def test_checkout_paid_checkbox_uses_indicator_check_not_text_icon(self):
        checkout = CheckoutDialog(
            device_name="小包1",
            type_name="小包",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-28 11:48:49",
            elapsed_seconds=3600,
        )
        try:
            checkbox_style = checkout.paid_checkbox.styleSheet()

            self.assertEqual(checkout.paid_checkbox.text(), "已付款（勾选表示客户已完成付款）")
            self.assertNotIn("✅", checkout.paid_checkbox.text())
            self.assertIn("QCheckBox::indicator:checked", checkbox_style)
            self.assertIn("checkbox_checked.svg", checkbox_style)
            self.assertIn(f"border: 2px solid {COLORS['success']}", checkbox_style)
        finally:
            checkout.deleteLater()

    def test_checkout_confirm_button_has_hover_and_pressed_feedback(self):
        checkout = CheckoutDialog(
            device_name="小包1",
            type_name="小包",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-28 11:48:49",
            elapsed_seconds=3600,
        )
        try:
            confirm_btn = next(
                button
                for button in checkout.findChildren(QPushButton)
                if button.text() == "确认结束"
            )
            style = confirm_btn.styleSheet()

            self.assertNotIn("✓", confirm_btn.text())
            self.assertFalse(confirm_btn.icon().isNull())
            self.assertGreaterEqual(confirm_btn.iconSize().width(), 18)
            self.assertGreaterEqual(confirm_btn.iconSize().height(), 18)
            self.assertIs(confirm_btn.property("usesVectorConfirmIcon"), True)
            self.assertEqual(confirm_btn.cursor().shape(), Qt.CursorShape.PointingHandCursor)
            self.assertIn("QPushButton:hover", style)
            self.assertIn("background: #A7FBFF", style)
            self.assertIn("QPushButton:pressed", style)
            self.assertIn("background: #5DE8F0", style)
        finally:
            checkout.deleteLater()

    def test_dark_styles_do_not_keep_light_panel_fills(self):
        panel = DevicePanel.__new__(DevicePanel)
        stats_panel = StatsPanel.__new__(StatsPanel)
        active_card = DeviceCard(
            device_id=3,
            device_name="灏忓寘3",
            type_name="灏忓寘",
            status=DeviceStatus.ACTIVE,
        )
        dialog = CheckoutDialog(
            device_name="灏忓寘3",
            type_name="灏忓寘",
            timer_mode=TimerMode.FREEPLAY,
            start_time="2026-04-27 10:00:00",
            elapsed_seconds=3600,
        )
        try:
            combined = "\n".join(
                [
                    DevicePanel._panel_style(panel),
                    DevicePanel._ghost_button_style(panel),
                    StatsPanel._panel_style(stats_panel),
                    StatsPanel._table_style(stats_panel),
                    active_card._card_frame_styles["base"],
                    active_card._card_frame_styles["blink"],
                    active_card.status_label.styleSheet(),
                    dialog.styleSheet(),
                    dialog.paid_checkbox.styleSheet(),
                ]
            )
            for light_fill in ("#FFFFFF", "#F6F8FB", "#F8FAFC", "#F1F5F9", "#EEF2FF", "background: white"):
                self.assertNotIn(light_fill, combined)
            self.assertIn(COLORS["surface_alt"], active_card.status_label.styleSheet())
            self.assertIn(COLORS["border_soft"], StatsPanel._table_style(stats_panel))
            self.assertIn(COLORS["surface"], dialog.paid_checkbox.styleSheet())
        finally:
            active_card.deleteLater()
            dialog.deleteLater()

    def test_frame_styles_target_outer_containers_without_label_borders(self):
        panel = DevicePanel.__new__(DevicePanel)
        stats_panel = StatsPanel.__new__(StatsPanel)
        card = DeviceCard(
            device_id=2,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.ACTIVE,
        )
        try:
            self.assertIn("QFrame#panelCard", DevicePanel._panel_style(panel))
            self.assertNotIn("QFrame {", DevicePanel._panel_style(panel))
            self.assertIn("QFrame#panelCard QLabel", DevicePanel._panel_style(panel))
            self.assertIn("QFrame#panelCard", StatsPanel._panel_style(stats_panel))
            self.assertNotIn("QFrame {", StatsPanel._panel_style(stats_panel))
            self.assertIn("QFrame#panelCard QLabel", StatsPanel._panel_style(stats_panel))
            self.assertEqual(card._timer_frame.objectName(), "timerFrame")
            self.assertIn("QFrame#timerFrame", card._timer_frame.styleSheet())
            self.assertIn("QFrame#timerFrame QLabel", card._timer_frame.styleSheet())
        finally:
            card.deleteLater()


if __name__ == "__main__":
    unittest.main()
