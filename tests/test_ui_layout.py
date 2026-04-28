import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLabel, QHeaderView, QPushButton, QSizePolicy, QSpinBox, QToolButton

from database import db_manager as db
from config import ASSETS_DIR, COLORS, DeviceStatus, TimerMode
from ui import device_panel as device_panel_module
from ui.device_card import DeviceCard
from ui.device_panel import DevicePanel, StartTimerDialog
from ui.stats_panel import StatsPanel


class DeviceCardLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        self.card.deleteLater()

    def test_comfortable_layout_reserves_space_for_timer_and_actions(self):
        self.card = DeviceCard(
            device_id=1,
            device_name="小包1",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.card.set_density_mode("comfortable")

        self.assertEqual(self.card.width(), 292)
        self.assertEqual(self.card.height(), 326)
        self.assertEqual(self.card._timer_frame.height(), 96)
        for button in self.card._action_buttons:
            self.assertEqual(button.height(), 36)

    def test_card_surface_returns_to_arrow_cursor_after_start_button_hides(self):
        self.card = DeviceCard(
            device_id=25,
            device_name="小包25",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.assertEqual(self.card.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertEqual(
            self.card.start_btn.cursor().shape(),
            Qt.CursorShape.PointingHandCursor,
        )

        self.card.start_timer(session_id=115, mode=TimerMode.FREEPLAY)

        self.assertTrue(self.card.start_btn.isHidden())
        self.assertEqual(self.card.cursor().shape(), Qt.CursorShape.ArrowCursor)

    def test_session_note_is_displayed_on_running_card_and_cleared_on_stop(self):
        self.card = DeviceCard(
            device_id=7,
            device_name="小包7",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(
            session_id=100,
            mode=TimerMode.COUNTDOWN,
            countdown_seconds=3600,
            note="团购码 A123",
        )

        self.assertFalse(self.card.session_note_label.isHidden())
        self.assertEqual(self.card.session_note_label.text(), "备注：团购码 A123")

        self.card.stop_timer()

        self.assertTrue(self.card.session_note_label.isHidden())
        self.assertEqual(self.card.session_note_label.text(), "")

    def test_freeplay_timer_shows_cumulative_context_inline_without_runtime_hint(self):
        self.card = DeviceCard(
            device_id=9,
            device_name="测试包厢9",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(session_id=102, mode=TimerMode.FREEPLAY)

        self.assertEqual(self.card.time_context_label.text(), "累计用时")
        self.assertTrue(self.card.runtime_hint_label.isHidden())
        self.assertNotIn("已玩", self.card.runtime_hint_label.text())

    def test_countdown_timer_shows_remaining_context_inline_without_runtime_hint(self):
        self.card = DeviceCard(
            device_id=10,
            device_name="测试包厢10",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(
            session_id=103,
            mode=TimerMode.COUNTDOWN,
            countdown_seconds=3600,
        )

        self.assertEqual(self.card.time_context_label.text(), "剩余时间")
        self.assertTrue(self.card.runtime_hint_label.isHidden())
        self.assertNotIn("剩余", self.card.runtime_hint_label.text())

    def test_timer_mode_label_is_stacked_below_status_badge(self):
        self.card = DeviceCard(
            device_id=11,
            device_name="测试包厢11",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(
            session_id=104,
            mode=TimerMode.COUNTDOWN,
            countdown_seconds=3600,
        )

        self.assertEqual(self.card._status_column.itemAt(0).widget(), self.card.status_label)
        self.assertEqual(self.card._status_column.itemAt(1).widget(), self.card.mode_label)
        self.assertEqual(self.card.mode_label.text(), TimerMode.LABELS[TimerMode.COUNTDOWN])

    def test_restored_session_note_is_displayed_on_card(self):
        from datetime import datetime

        self.card = DeviceCard(
            device_id=8,
            device_name="小包8",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.card.restore_session(
            session_id=101,
            mode=TimerMode.FREEPLAY,
            countdown_seconds=0,
            start_time=datetime.now(),
            pause_duration=0,
            is_paused=False,
            note="老客备注",
        )

        self.assertFalse(self.card.session_note_label.isHidden())
        self.assertEqual(self.card.session_note_label.text(), "备注：老客备注")

    def test_timer_font_fit_keeps_label_height_stable_for_long_runtime(self):
        self.card = DeviceCard(
            device_id=2,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.ACTIVE,
        )
        self.card.set_density_mode("comfortable")
        self.card.time_label.resize(230, 40)
        self.card.time_label.setText("685:46:22")

        self.card._fit_time_font()

        self.assertLessEqual(self.card.time_label.height(), 48)

    def test_comfortable_timer_uses_larger_font_for_normal_runtime(self):
        self.card = DeviceCard(
            device_id=12,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.ACTIVE,
        )
        self.card.set_density_mode("comfortable")
        self.card.start_timer(session_id=105, mode=TimerMode.FREEPLAY)
        self.card.show()
        self.app.processEvents()
        self.card.time_label.setText("00:29:17")

        self.card._fit_time_font()

        self.assertGreaterEqual(self.card.time_label.font().pointSize(), 18)
        self.assertEqual(self.card.time_label.height(), 48)

    def test_device_type_badge_keeps_fixed_height_on_idle_cards(self):
        self.card = DeviceCard(
            device_id=13,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        self.card.set_density_mode("comfortable")
        self.card.show()
        self.app.processEvents()

        self.assertEqual(self.card.type_label.height(), 28)
        self.assertEqual(self.card.type_label.minimumHeight(), 28)
        self.assertEqual(self.card.type_label.maximumHeight(), 28)
        self.assertEqual(self.card.type_label.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Fixed)

    def test_timer_context_text_bottom_aligns_with_time_text_bottom(self):
        self.card = DeviceCard(
            device_id=14,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )
        self.card.set_density_mode("comfortable")
        self.card.start_timer(session_id=106, mode=TimerMode.FREEPLAY)
        self.card.show()
        self.app.processEvents()

        time_metrics = QFontMetrics(self.card.time_label.font())
        time_text_bottom = (
            self.card.time_label.geometry().top()
            + (self.card.time_label.height() - time_metrics.height()) // 2
            + time_metrics.height()
        )
        context_text_bottom = (
            self.card.time_context_label.geometry().bottom()
            + 1
        )

        self.assertLessEqual(
            abs(context_text_bottom - time_text_bottom),
            1,
        )

    def test_timer_context_label_uses_readable_size_without_cropping(self):
        self.card = DeviceCard(
            device_id=20,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )
        self.card.start_timer(session_id=110, mode=TimerMode.FREEPLAY)
        self.card.show()
        self.app.processEvents()

        self.assertIn("font-size: 12px", self.card.time_context_label.styleSheet())
        self.assertEqual(self.card.time_context_label.width(), 52)
        self.assertLessEqual(
            self.card.time_context_label.sizeHint().width(),
            self.card.time_context_label.width(),
        )

    def test_expired_countdown_uses_positive_overtime_with_overtime_context(self):
        from datetime import datetime, timedelta

        self.card = DeviceCard(
            device_id=22,
            device_name="小包1",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(
            session_id=112,
            mode=TimerMode.COUNTDOWN,
            countdown_seconds=60,
            start_time=datetime.now() - timedelta(seconds=75),
        )

        self.assertEqual(self.card.time_label.text(), "00:00:15")
        self.assertFalse(self.card.time_label.text().startswith("-"))
        self.assertEqual(self.card.time_context_label.text(), "超时时间")
        self.assertIn("font-size: 12px", self.card.time_context_label.styleSheet())

    def test_countdown_time_stays_white_until_expired(self):
        from datetime import datetime, timedelta

        self.card = DeviceCard(
            device_id=26,
            device_name="小包26",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        self.card.start_timer(
            session_id=116,
            mode=TimerMode.COUNTDOWN,
            countdown_seconds=600,
            start_time=datetime.now() - timedelta(seconds=60),
        )
        self.card._apply_time_label_style(self.card.timer.get_remaining_seconds())

        self.assertIn(f"color: {COLORS['text_dark']}", self.card.time_label.styleSheet())

        self.card.timer.countdown_seconds = 240
        self.card._apply_time_label_style(240)

        self.assertIn(f"color: {COLORS['text_dark']}", self.card.time_label.styleSheet())
        self.assertNotIn(COLORS["secondary"], self.card.time_label.styleSheet())
        self.assertNotIn(COLORS["warning"], self.card.time_label.styleSheet())

    def test_running_time_row_sits_closer_to_top_of_timer_frame(self):
        self.card = DeviceCard(
            device_id=21,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        self.card.set_density_mode("comfortable")
        self.card.start_timer(session_id=111, mode=TimerMode.FREEPLAY, note="杨凡在玩")
        self.card.show()
        self.app.processEvents()

        time_top = self.card.time_label.mapTo(
            self.card._timer_frame,
            self.card.time_label.rect().topLeft(),
        ).y()

        self.assertLessEqual(time_top, 24)

    def test_paused_timer_time_is_muted(self):
        self.card = DeviceCard(
            device_id=23,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        self.card.start_timer(session_id=113, mode=TimerMode.FREEPLAY)

        self.card.pause_timer()

        self.assertEqual(self.card.status_label.text(), "已暂停")
        self.assertIn(f"color: {COLORS['text_muted']}", self.card.time_label.styleSheet())

    def test_resumed_timer_time_restores_running_color_immediately(self):
        self.card = DeviceCard(
            device_id=24,
            device_name="小包3",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        self.card.start_timer(session_id=114, mode=TimerMode.FREEPLAY)
        self.card.pause_timer()

        self.card.resume_timer()

        self.assertEqual(self.card.status_label.text(), "使用中")
        self.assertIn(f"color: {COLORS['text_dark']}", self.card.time_label.styleSheet())

    def test_idle_timer_placeholder_is_center_aligned(self):
        self.card = DeviceCard(
            device_id=18,
            device_name="小包3",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        self.card.set_density_mode("comfortable")
        self.card.show()
        self.app.processEvents()

        self.assertEqual(self.card.time_label.text(), "--:--:--")
        self.assertIn(f"color: {COLORS['text_muted']}", self.card.time_label.styleSheet())
        self.assertTrue(self.card.time_label.alignment() & Qt.AlignmentFlag.AlignHCenter)
        self.assertFalse(self.card.time_label.alignment() & Qt.AlignmentFlag.AlignRight)

    def test_running_timer_remains_right_aligned_for_context_label(self):
        self.card = DeviceCard(
            device_id=19,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )
        self.card.start_timer(session_id=109, mode=TimerMode.FREEPLAY)

        self.assertTrue(self.card.time_label.alignment() & Qt.AlignmentFlag.AlignRight)
        self.assertFalse(self.card.time_label.alignment() & Qt.AlignmentFlag.AlignHCenter)

    def test_header_badge_and_timer_frame_positions_are_fixed_across_states(self):
        self.card = DeviceCard(
            device_id=15,
            device_name="奥特曼包厢",
            type_name="大包",
            status=DeviceStatus.IDLE,
        )
        self.card.start_timer(session_id=107, mode=TimerMode.FREEPLAY, note="测试计时")

        expired_card = DeviceCard(
            device_id=16,
            device_name="小包1",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        idle_card = DeviceCard(
            device_id=17,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )
        try:
            expired_card.start_timer(
                session_id=108,
                mode=TimerMode.COUNTDOWN,
                countdown_seconds=60,
            )
            expired_card._status = DeviceStatus.EXPIRED
            expired_card._apply_status_style()

            cards = [self.card, expired_card, idle_card]
            for card in cards:
                card.set_density_mode("comfortable")
                card.show()
            self.app.processEvents()

            type_tops = {card.type_label.geometry().top() for card in cards}
            timer_tops = [card._timer_frame.geometry().top() for card in cards]

            self.assertEqual(type_tops, {self.card.type_label.geometry().top()})
            self.assertLessEqual(max(timer_tops) - min(timer_tops), 1)
        finally:
            expired_card.deleteLater()
            idle_card.deleteLater()

    def test_drag_payload_contains_device_id(self):
        self.card = DeviceCard(
            device_id=42,
            device_name="小包2",
            type_name="小包",
            status=DeviceStatus.IDLE,
        )

        mime = self.card._drag_mime_data()

        self.assertTrue(mime.hasFormat("application/x-videogame-device-id"))
        self.assertEqual(
            bytes(mime.data("application/x-videogame-device-id")).decode("utf-8"),
            "42",
        )


class DevicePanelLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "layout.db")
        db.init_db()
        db.migrate_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_columns_for_width_fills_available_space(self):
        self.assertEqual(DevicePanel._columns_for_width(280, 292, 18), 1)
        self.assertEqual(DevicePanel._columns_for_width(620, 292, 18), 2)
        self.assertEqual(DevicePanel._columns_for_width(930, 292, 18), 3)
        self.assertEqual(DevicePanel._columns_for_width(1240, 292, 18), 4)

    def test_move_device_id_reorders_before_target_or_to_end(self):
        self.assertEqual(DevicePanel._move_device_id([1, 2, 3, 4], 3, 2), [1, 3, 2, 4])
        self.assertEqual(DevicePanel._move_device_id([1, 2, 3, 4], 2, None), [1, 3, 4, 2])
        self.assertEqual(DevicePanel._move_device_id([1, 2, 3, 4], 2, 2), [1, 2, 3, 4])
        self.assertEqual(DevicePanel._move_device_id([1, 2, 3, 4], 9, 1), [1, 2, 3, 4])

    def test_dashboard_omits_right_side_text_panels(self):
        panel = DevicePanel()
        try:
            self.assertFalse(hasattr(panel, "_insight_panel"))
            self.assertFalse(hasattr(panel, "_pending_panel"))
            self.assertFalse(hasattr(panel, "_legend_panel"))

            panel.refresh_dashboard()
        finally:
            panel.deleteLater()

    def test_dashboard_summary_chips_are_short_and_full_width(self):
        panel = DevicePanel()
        try:
            self.assertEqual(len(panel._summary_chips), 4)
            for chip in panel._summary_chips:
                self.assertEqual(chip.height(), 68)
                self.assertEqual(chip.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Expanding)
                self.assertNotEqual(chip.maximumWidth(), 180)
        finally:
            panel.deleteLater()

    def test_dashboard_header_omits_start_new_timer_button(self):
        panel = DevicePanel()
        try:
            button_texts = {button.text() for button in panel.findChildren(QPushButton)}

            self.assertIn("刷新状态", button_texts)
            self.assertNotIn("开始新计时", button_texts)
            self.assertFalse(hasattr(panel, "_focus_btn"))
            self.assertFalse(hasattr(panel, "_focus_first_idle"))
        finally:
            panel.deleteLater()

    def test_dashboard_blank_surfaces_use_arrow_cursor(self):
        panel = DevicePanel()
        try:
            self.assertEqual(panel.cursor().shape(), Qt.CursorShape.ArrowCursor)
            self.assertEqual(panel._scroll.cursor().shape(), Qt.CursorShape.ArrowCursor)
            self.assertEqual(panel._scroll.viewport().cursor().shape(), Qt.CursorShape.ArrowCursor)
            self.assertEqual(panel._grid_widget.cursor().shape(), Qt.CursorShape.ArrowCursor)

            scroll_style = panel._scroll.styleSheet()
            self.assertIn("QScrollBar:vertical", scroll_style)
            self.assertIn("width: 12px", scroll_style)
            self.assertIn(f"background: {COLORS['card_bg']}", scroll_style)
            self.assertIn(f"background: {COLORS['border']}", scroll_style)
            self.assertIn(f"background: {COLORS['accent']}", scroll_style)
            self.assertIn("height: 0", scroll_style)
        finally:
            panel.deleteLater()

    def test_canceling_start_timer_dialog_refreshes_cursor(self):
        type_id = db.add_device_type("测试类型")
        device_id = db.add_device("测试包厢", type_id)
        panel = DevicePanel()

        class CancelStartTimerDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec(self):
                return 0

        original_dialog = device_panel_module.StartTimerDialog
        try:
            calls = []
            device_panel_module.StartTimerDialog = CancelStartTimerDialog
            panel._refresh_cursor_after_action = lambda: calls.append("refreshed")

            panel._on_start(device_id)

            self.assertEqual(calls, ["refreshed"])
            self.assertIsNone(db.get_active_session(device_id))
        finally:
            device_panel_module.StartTimerDialog = original_dialog
            panel.deleteLater()

    def test_start_timer_countdown_mode_button_has_readable_checked_text(self):
        dialog = StartTimerDialog("测试包厢")
        try:
            dialog._select_mode(TimerMode.COUNTDOWN)
            style = dialog._btn_countdown.styleSheet()

            self.assertTrue(dialog._btn_countdown.isChecked())
            self.assertIn(f"background: {COLORS['surface_alt']}", style)
            self.assertIn("color: #FFFFFF", style)
            self.assertNotIn(f"color: {COLORS['countdown']};\n                font-weight", style)
        finally:
            dialog.deleteLater()

    def test_start_timer_primary_button_has_hover_and_pressed_feedback(self):
        dialog = StartTimerDialog("测试包厢")
        try:
            dialog._select_mode(TimerMode.FREEPLAY)
            style = dialog._start_btn.styleSheet()

            self.assertEqual(dialog._start_btn.text(), "开始自由计时")
            self.assertNotIn("▶", dialog._start_btn.text())
            self.assertFalse(dialog._start_btn.icon().isNull())
            self.assertGreaterEqual(dialog._start_btn.iconSize().width(), 18)
            self.assertGreaterEqual(dialog._start_btn.iconSize().height(), 18)
            self.assertIs(dialog._start_btn.property("usesVectorStartIcon"), True)
            self.assertEqual(dialog._start_btn.cursor().shape(), Qt.CursorShape.PointingHandCursor)
            self.assertIn("QPushButton:hover", style)
            self.assertIn("background: #A7FBFF", style)
            self.assertIn("QPushButton:pressed", style)
            self.assertIn("background: #5DE8F0", style)
        finally:
            dialog.deleteLater()

    def test_countdown_panel_text_labels_have_transparent_backgrounds(self):
        dialog = StartTimerDialog("测试包厢")
        try:
            labels_by_text = {label.text(): label for label in dialog.findChildren(QLabel)}

            for text in ("选择套餐时长", "自定义：", "分钟", "未选择"):
                self.assertIn(text, labels_by_text)
                style = labels_by_text[text].styleSheet()
                self.assertIn("background: transparent", style)
                self.assertIn("border: none", style)
        finally:
            dialog.deleteLater()


class StatsPanelLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "stats-layout.db")
        db.init_db()
        db.migrate_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def _create_completed_session(
        self,
        device_name: str,
        type_name: str,
        total_seconds: int,
        paid: bool = True,
        mode: str = TimerMode.FREEPLAY,
    ):
        type_id = db.add_device_type(type_name)
        device_id = db.add_device(device_name, type_id)
        session_id = db.start_session(device_id, mode)
        db.end_session(
            session_id,
            device_id,
            total_seconds=total_seconds,
            paid=paid,
        )
        return device_id

    def test_history_note_column_is_wide_and_editable_in_dark_mode(self):
        panel = StatsPanel()
        try:
            header = panel.history_table.horizontalHeader()
            self.assertEqual(header.sectionResizeMode(0), QHeaderView.ResizeMode.Interactive)
            self.assertEqual(header.sectionResizeMode(7), QHeaderView.ResizeMode.Stretch)
            self.assertGreaterEqual(panel.history_table.verticalHeader().defaultSectionSize(), 40)
            self.assertGreaterEqual(panel.history_table.columnWidth(3), 150)
            self.assertGreaterEqual(panel.history_table.columnWidth(7), 240)

            table_style = panel.history_table.styleSheet()
            self.assertIn("QTableWidget QLineEdit", table_style)
            self.assertIn("min-height: 24px", table_style)
            self.assertIn("padding: 1px 10px", table_style)
            self.assertIn("selection-background-color: #245C66", table_style)
            self.assertIn(f"selection-color: {COLORS['text_dark']}", table_style)
        finally:
            panel.deleteLater()

    def test_report_tables_use_larger_readable_text(self):
        panel = StatsPanel()
        try:
            for table in (panel.device_table, panel.history_table):
                table_style = table.styleSheet()
                self.assertIn("QTableWidget {", table_style)
                self.assertIn("QHeaderView::section", table_style)
                self.assertIn("font-size: 13px;", table_style)
                self.assertNotIn("font-size: 12px;", table_style)
        finally:
            panel.deleteLater()

    def test_report_tables_use_dark_custom_scrollbars(self):
        panel = StatsPanel()
        try:
            for table in (panel.device_table, panel.history_table):
                table_style = table.styleSheet()

                self.assertIn("QTableWidget QScrollBar:vertical", table_style)
                self.assertIn("QTableWidget QScrollBar::handle:vertical", table_style)
                self.assertIn("QTableWidget QScrollBar:horizontal", table_style)
                self.assertIn("QTableWidget QTableCornerButton::section", table_style)
                self.assertIn("width: 12px", table_style)
                self.assertIn("height: 12px", table_style)
                self.assertIn(f"background: {COLORS['card_bg']}", table_style)
                self.assertIn(f"background: {COLORS['border']}", table_style)
                self.assertIn(f"background: {COLORS['accent']}", table_style)
                self.assertIn("height: 0", table_style)
                self.assertIn("width: 0", table_style)
        finally:
            panel.deleteLater()

    def test_device_overview_selection_has_room_without_inner_focus_box(self):
        panel = StatsPanel()
        try:
            self.assertGreaterEqual(panel.device_table.verticalHeader().defaultSectionSize(), 40)
            self.assertGreaterEqual(panel.device_table.verticalHeader().minimumSectionSize(), 40)

            table_style = panel.device_table.styleSheet()
            self.assertIn("QTableWidget::item:focus", table_style)
            self.assertIn("border: none", table_style)
            self.assertNotIn("QTableWidget::item:focus {\n                border: 1px", table_style)
        finally:
            panel.deleteLater()

    def test_device_overview_single_click_filters_history_by_device(self):
        self._create_completed_session("奥特曼包厢", "大包", 3600)
        self._create_completed_session("小包2", "小包", 600)

        panel = StatsPanel()
        try:
            self.assertEqual(panel.history_table.rowCount(), 2)
            self.assertEqual(panel.device_table.item(0, 0).text(), "奥特曼包厢")

            panel.device_table.cellClicked.emit(0, 0)

            self.assertEqual(panel._history_device_filter, "奥特曼包厢")
            self.assertEqual(panel.history_table.rowCount(), 1)
            self.assertEqual(panel.history_table.item(0, 0).text(), "奥特曼包厢")
        finally:
            panel.deleteLater()

    def test_history_all_button_clears_device_filter(self):
        self._create_completed_session("奥特曼包厢", "大包", 3600)
        self._create_completed_session("小包2", "小包", 600)

        panel = StatsPanel()
        try:
            self.assertEqual(panel.history_all_btn.text(), "全部")

            panel.device_table.cellClicked.emit(0, 0)
            self.assertEqual(panel.history_table.rowCount(), 1)

            panel.history_all_btn.click()

            self.assertIsNone(panel._history_device_filter)
            self.assertEqual(panel.history_table.rowCount(), 2)
            self.assertEqual(
                {panel.history_table.item(row, 0).text() for row in range(panel.history_table.rowCount())},
                {"奥特曼包厢", "小包2"},
            )
        finally:
            panel.deleteLater()

    def test_stats_summary_cards_are_removed_from_stats_page(self):
        panel = StatsPanel()
        try:
            self.assertFalse(hasattr(panel, "_payment_summary"))
            self.assertFalse(hasattr(panel, "_mode_summary"))

            panel.refresh()
        finally:
            panel.deleteLater()

    def test_stats_metric_cards_are_short_and_include_mode_counts(self):
        panel = StatsPanel()
        try:
            self.assertEqual(len(panel._metric_cards), 6)
            self.assertNotIn("countdown_share", panel._metric_values)
            self.assertIn("countdown_count", panel._metric_values)
            self.assertIn("freeplay_count", panel._metric_values)
            self.assertIn("unpaid_count", panel._metric_values)
            for card in panel._metric_cards:
                self.assertEqual(card.height(), 68)
                self.assertEqual(card.sizePolicy().horizontalPolicy(), QSizePolicy.Policy.Expanding)

            self.assertEqual(panel._metric_values["countdown_count"].text(), "0")
            self.assertEqual(panel._metric_values["freeplay_count"].text(), "0")
            self.assertEqual(panel._metric_values["unpaid_count"].text(), "0")
        finally:
            panel.deleteLater()

    def test_total_count_card_is_default_selected_metric(self):
        panel = StatsPanel()
        try:
            active_border = f"border: 1px solid {COLORS['accent']}"
            inactive_border = f"border: 1px solid {COLORS['border']}"

            self.assertIsNone(panel._metric_filter_key)
            self.assertIn(active_border, panel._metric_cards_by_key["total_count"].styleSheet())

            panel._metric_cards_by_key["unpaid_count"].clicked.emit("unpaid_count")

            self.assertIn(inactive_border, panel._metric_cards_by_key["total_count"].styleSheet())
            self.assertIn(active_border, panel._metric_cards_by_key["unpaid_count"].styleSheet())

            panel._metric_cards_by_key["total_count"].clicked.emit("total_count")

            self.assertIsNone(panel._metric_filter_key)
            self.assertIn(active_border, panel._metric_cards_by_key["total_count"].styleSheet())
            self.assertIn(inactive_border, panel._metric_cards_by_key["unpaid_count"].styleSheet())
        finally:
            panel.deleteLater()

    def test_stats_mode_and_unpaid_counts_are_displayed(self):
        type_id = db.get_all_device_types()[0]["id"]
        device_id = db.add_device("测试包厢", type_id)
        paid_session = db.start_session(device_id, TimerMode.FREEPLAY)
        db.end_session(paid_session, device_id, total_seconds=1800, paid=True)
        unpaid_session = db.start_session(device_id, TimerMode.COUNTDOWN, countdown_seconds=3600)
        db.end_session(unpaid_session, device_id, total_seconds=2400, paid=False)

        panel = StatsPanel()
        try:
            self.assertEqual(panel._metric_values["total_count"].text(), "2")
            self.assertEqual(panel._metric_values["countdown_count"].text(), "1")
            self.assertEqual(panel._metric_values["freeplay_count"].text(), "1")
            self.assertEqual(panel._metric_values["paid_count"].text(), "1")
            self.assertEqual(panel._metric_values["unpaid_count"].text(), "1")
        finally:
            panel.deleteLater()

    def test_metric_card_single_click_filters_device_overview_and_history(self):
        type_id = db.add_device_type("过滤测试")
        device_a = db.add_device("团购已付包厢", type_id)
        session_a = db.start_session(device_a, TimerMode.COUNTDOWN, countdown_seconds=3600)
        db.end_session(session_a, device_a, total_seconds=3600, paid=True)
        device_b = db.add_device("自由未付包厢", type_id)
        session_b = db.start_session(device_b, TimerMode.FREEPLAY)
        db.end_session(session_b, device_b, total_seconds=1800, paid=False)
        device_c = db.add_device("团购未付包厢", type_id)
        session_c = db.start_session(device_c, TimerMode.COUNTDOWN, countdown_seconds=5400)
        db.end_session(session_c, device_c, total_seconds=5400, paid=False)

        panel = StatsPanel()
        try:
            self.assertEqual(panel.device_table.rowCount(), 3)
            self.assertEqual(panel.history_table.rowCount(), 3)

            panel._metric_cards_by_key["countdown_count"].clicked.emit("countdown_count")

            self.assertEqual(panel._metric_filter_key, "countdown_count")
            self.assertEqual(panel.device_table.rowCount(), 2)
            self.assertEqual(panel.history_table.rowCount(), 2)
            self.assertEqual(
                {panel.device_table.item(row, 0).text() for row in range(panel.device_table.rowCount())},
                {"团购已付包厢", "团购未付包厢"},
            )
            self.assertEqual(
                {panel.history_table.item(row, 2).text() for row in range(panel.history_table.rowCount())},
                {"团购套餐"},
            )

            panel._metric_cards_by_key["unpaid_count"].clicked.emit("unpaid_count")

            self.assertEqual(panel._metric_filter_key, "unpaid_count")
            self.assertEqual(panel.device_table.rowCount(), 2)
            self.assertEqual(panel.history_table.rowCount(), 2)
            self.assertEqual(
                {panel.device_table.item(row, 0).text() for row in range(panel.device_table.rowCount())},
                {"自由未付包厢", "团购未付包厢"},
            )
            self.assertEqual(
                {panel.history_table.item(row, 5).text() for row in range(panel.history_table.rowCount())},
                {"未付"},
            )
        finally:
            panel.deleteLater()

    def test_total_metric_cards_clear_metric_filter_without_clearing_device_filter(self):
        type_id = db.add_device_type("组合过滤测试")
        device_a = db.add_device("团购包厢", type_id)
        session_a = db.start_session(device_a, TimerMode.COUNTDOWN, countdown_seconds=3600)
        db.end_session(session_a, device_a, total_seconds=3600, paid=True)
        device_b = db.add_device("自由包厢", type_id)
        session_b = db.start_session(device_b, TimerMode.FREEPLAY)
        db.end_session(session_b, device_b, total_seconds=1800, paid=False)

        panel = StatsPanel()
        try:
            panel._metric_cards_by_key["freeplay_count"].clicked.emit("freeplay_count")
            self.assertEqual(panel.device_table.rowCount(), 1)
            panel.device_table.cellClicked.emit(0, 0)
            self.assertEqual(panel._history_device_filter, "自由包厢")
            self.assertEqual(panel.history_table.rowCount(), 1)

            panel._metric_cards_by_key["total_count"].clicked.emit("total_count")

            self.assertIsNone(panel._metric_filter_key)
            self.assertEqual(panel.device_table.rowCount(), 2)
            self.assertEqual(panel._history_device_filter, "自由包厢")
            self.assertEqual(panel.history_table.rowCount(), 1)
            self.assertEqual(panel.history_table.item(0, 0).text(), "自由包厢")

            panel._metric_cards_by_key["paid_count"].clicked.emit("paid_count")
            self.assertEqual(panel._metric_filter_key, "paid_count")
            panel._metric_cards_by_key["total_hours"].clicked.emit("total_hours")
            self.assertIsNone(panel._metric_filter_key)
        finally:
            panel.deleteLater()

    def test_history_note_items_are_left_aligned_for_editing(self):
        panel = StatsPanel()
        try:
            item = panel._make_table_item("editable note", editable=True, align_left=True)

            self.assertTrue(item.textAlignment() & Qt.AlignmentFlag.AlignLeft)
            self.assertTrue(item.flags() & Qt.ItemFlag.ItemIsEditable)
        finally:
            panel.deleteLater()

    def test_stats_filter_date_range_controls_have_readable_width(self):
        panel = StatsPanel()
        try:
            self.assertGreaterEqual(panel.date_from.minimumWidth(), 126)
            self.assertGreaterEqual(panel.date_to.minimumWidth(), 126)

            separator = panel.findChild(QLabel, "dateRangeSeparator")
            self.assertIsNotNone(separator)
            self.assertGreaterEqual(separator.minimumWidth(), 22)
            separator_style = separator.styleSheet()
            self.assertIn(COLORS["text_dark"], separator_style)
            self.assertIn("background: transparent", separator_style)
            self.assertIn("border: none", separator_style)
        finally:
            panel.deleteLater()

    def test_stats_date_inputs_keep_focus_border_through_dropdown_area(self):
        panel = StatsPanel()
        try:
            arrow_path = Path(ASSETS_DIR, "dropdown_arrow.png")
            arrow_url = arrow_path.as_posix()

            self.assertTrue(arrow_path.is_file())
            for edit in (panel.date_from, panel.date_to):
                style = edit.styleSheet()

                self.assertTrue(edit.alignment() & Qt.AlignmentFlag.AlignHCenter)
                self.assertIn("padding: 4px 10px", style)
                self.assertIn("QDateEdit::drop-down", style)
                self.assertIn("subcontrol-origin: border", style)
                self.assertIn("subcontrol-position: top right", style)
                self.assertIn("background: transparent", style)
                self.assertIn("border: none", style)
                self.assertIn("margin: 1px 1px 1px 0", style)
                self.assertIn("QDateEdit::down-arrow", style)
                self.assertIn(f"image: url({arrow_url})", style)
                self.assertIn("width: 10px", style)
                self.assertIn("height: 7px", style)
                self.assertIn("margin-right: 7px", style)
        finally:
            panel.deleteLater()

    def test_stats_date_popup_calendar_uses_readable_dark_theme(self):
        panel = StatsPanel()
        try:
            for edit in (panel.date_from, panel.date_to):
                calendar_style = edit.calendarWidget().styleSheet()

                self.assertIn("QCalendarWidget", calendar_style)
                self.assertIn("QAbstractItemView", calendar_style)
                self.assertIn(f"color: {COLORS['text_dark']}", calendar_style)
                self.assertIn(f"background: {COLORS['card_bg']}", calendar_style)
                self.assertIn(f"selection-background-color: {COLORS['accent']}", calendar_style)
        finally:
            panel.deleteLater()

    def test_stats_date_popup_year_spinbox_has_large_stepper_hit_area(self):
        panel = StatsPanel()
        try:
            up_arrow = Path(ASSETS_DIR, "spinbox_arrow_up.png")
            down_arrow = Path(ASSETS_DIR, "spinbox_arrow_down.png")

            self.assertTrue(up_arrow.is_file())
            self.assertTrue(down_arrow.is_file())
            for edit in (panel.date_from, panel.date_to):
                calendar = edit.calendarWidget()
                year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
                calendar_style = calendar.styleSheet()

                self.assertIsNotNone(year_spinbox)
                self.assertGreaterEqual(year_spinbox.minimumWidth(), 96)
                self.assertGreaterEqual(year_spinbox.minimumHeight(), 28)
                self.assertIsNotNone(year_spinbox.findChild(QToolButton, "calendarYearStepUpButton"))
                self.assertIsNotNone(year_spinbox.findChild(QToolButton, "calendarYearStepDownButton"))
                self.assertIn("padding: 2px 30px 2px 8px", calendar_style)
                self.assertIn("QCalendarWidget QSpinBox::up-button", calendar_style)
                self.assertIn("QCalendarWidget QSpinBox::down-button", calendar_style)
                self.assertIn("subcontrol-origin: border", calendar_style)
                self.assertIn("subcontrol-position: top right", calendar_style)
                self.assertIn("subcontrol-position: bottom right", calendar_style)
                self.assertIn("width: 28px", calendar_style)
                self.assertIn("height: 14px", calendar_style)
                self.assertIn(f"image: url({up_arrow.as_posix()})", calendar_style)
                self.assertIn(f"image: url({down_arrow.as_posix()})", calendar_style)
        finally:
            panel.deleteLater()

    def test_stats_date_popup_year_stepper_buttons_change_year(self):
        panel = StatsPanel()
        try:
            calendar = panel.date_from.calendarWidget()
            year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
            up_button = year_spinbox.findChild(QToolButton, "calendarYearStepUpButton")
            down_button = year_spinbox.findChild(QToolButton, "calendarYearStepDownButton")

            self.assertIsNotNone(up_button)
            self.assertIsNotNone(down_button)
            calendar.show()
            self.app.processEvents()

            start_year = year_spinbox.value()
            up_button.click()
            self.app.processEvents()

            self.assertEqual(year_spinbox.value(), start_year + 1)
            self.assertEqual(calendar.yearShown(), start_year + 1)

            down_button.click()
            self.app.processEvents()

            self.assertEqual(year_spinbox.value(), start_year)
            self.assertEqual(calendar.yearShown(), start_year)
            self.assertGreaterEqual(up_button.x(), year_spinbox.width() - up_button.width() - 2)
            self.assertGreaterEqual(down_button.x(), year_spinbox.width() - down_button.width() - 2)
        finally:
            panel.deleteLater()

    def test_stats_date_popup_year_accepts_direct_numeric_entry(self):
        panel = StatsPanel()
        try:
            calendar = panel.date_from.calendarWidget()
            year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
            line_edit = year_spinbox.lineEdit()

            self.assertFalse(year_spinbox.isReadOnly())
            self.assertFalse(line_edit.isReadOnly())
            self.assertTrue(year_spinbox.focusPolicy() & Qt.FocusPolicy.StrongFocus)
            self.assertTrue(line_edit.focusPolicy() & Qt.FocusPolicy.StrongFocus)

            calendar.show()
            year_spinbox.setFocus(Qt.FocusReason.MouseFocusReason)
            year_spinbox.selectAll()
            self.app.processEvents()

            QTest.keyClicks(year_spinbox, "2024")
            self.app.processEvents()

            self.assertEqual(year_spinbox.text(), "2024")
            self.assertEqual(calendar.yearShown(), 2024)

            year_spinbox.selectAll()
            QTest.keyClicks(line_edit, "2031")
            self.app.processEvents()

            self.assertEqual(year_spinbox.text(), "2031")
            self.assertEqual(calendar.yearShown(), 2031)
        finally:
            panel.deleteLater()

    def test_stats_date_popup_month_arrow_buttons_are_white_text(self):
        panel = StatsPanel()
        try:
            expected = {
                "qt_calendar_prevmonth": "‹",
                "qt_calendar_nextmonth": "›",
            }
            for edit in (panel.date_from, panel.date_to):
                calendar = edit.calendarWidget()
                for object_name, text in expected.items():
                    button = calendar.findChild(QToolButton, object_name)

                    self.assertIsNotNone(button)
                    self.assertEqual(button.text(), text)
                    self.assertTrue(button.icon().isNull())
                    self.assertIn("color: #FFFFFF", button.styleSheet())
        finally:
            panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
