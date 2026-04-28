import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QFrame, QPushButton

from config import COLORS
from database import db_manager as db
from ui import settings_dialog as settings_module
from ui.settings_dialog import SettingsPanel, _DeviceEditDialog


class FakeTypeEditDialog:
    def __init__(self, name: str, accepted: bool = True):
        self.name = name
        self._accepted = accepted

    def exec(self):
        return self._accepted


class FakeDeviceEditDialog:
    def __init__(self, name: str, type_id: int, accepted: bool = True):
        self.name = name
        self.type_id = type_id
        self._accepted = accepted

    def exec(self):
        return self._accepted


class SettingsPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "settings.db")
        db.init_db()
        db.migrate_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_settings_page_uses_left_type_panel_and_right_device_panel(self):
        panel = SettingsPanel()
        try:
            self.assertFalse(hasattr(panel, "tabs"))
            self.assertEqual(panel._type_panel.objectName(), "settingsTypePanel")
            self.assertEqual(panel._type_panel.minimumWidth(), 360)
            self.assertEqual(panel._type_panel.maximumWidth(), 380)
            self.assertEqual(panel._device_panel.objectName(), "settingsDevicePanel")
            self.assertEqual(panel.type_table.columnCount(), 3)
            self.assertEqual(panel.device_table.columnCount(), 4)
            self.assertTrue(panel.testAttribute(Qt.WidgetAttribute.WA_StyledBackground))
            self.assertIn("background-color: #0B1118", panel.styleSheet())
        finally:
            panel.deleteLater()

    def test_settings_page_does_not_show_english_helper_labels(self):
        panel = SettingsPanel()
        try:
            label_text = "\n".join(label.text() for label in panel.findChildren(QLabel))
            for english_text in (
                "SYSTEM_CONFIG",
                "CONFIGURATION PROTOCOL",
                "ROOM TYPES AND ROOM FLEET",
                "TYPE CLASSIFICATION",
                "ROOM FLEET CONFIGURATION",
            ):
                self.assertNotIn(english_text, label_text)
        finally:
            panel.deleteLater()

    def test_settings_header_matches_other_pages_with_subtitle(self):
        panel = SettingsPanel()
        try:
            labels = {label.text(): label for label in panel.findChildren(QLabel)}

            self.assertIn("系统设置", labels)
            title_style = labels["系统设置"].styleSheet()
            self.assertIn("font-size: 28px", title_style)
            self.assertIn("font-weight: 800", title_style)
            self.assertIn(f"color: {COLORS['text_dark']}", title_style)
            self.assertNotIn("font-size: 34px", title_style)

            subtitle_text = "维护包厢类型、名称映射与基础状态，保持前台数据整洁一致。"
            self.assertIn(subtitle_text, labels)
            subtitle_style = labels[subtitle_text].styleSheet()
            self.assertIn("font-size: 13px", subtitle_style)
            self.assertIn(f"color: {COLORS['text_muted']}", subtitle_style)
        finally:
            panel.deleteLater()

    def test_settings_action_buttons_have_room_for_text(self):
        panel = SettingsPanel()
        try:
            self.assertGreaterEqual(panel.type_table.columnWidth(2), 126)
            self.assertLessEqual(panel.type_table.columnWidth(2), 138)
            self.assertGreaterEqual(panel.device_table.columnWidth(3), 126)
            self.assertLessEqual(panel.device_table.columnWidth(3), 138)

            action_cell = panel.type_table.cellWidget(0, 2)
            buttons = action_cell.findChildren(QPushButton)
            self.assertEqual([button.text() for button in buttons], ["修改", "删除"])
            for button in buttons:
                self.assertEqual(button.width(), 54)
                self.assertEqual(button.height(), 25)
        finally:
            panel.deleteLater()

    def test_settings_action_buttons_are_taller_and_vertically_centered(self):
        type_id = db.add_device_type("测试类型")
        db.add_device("测试包厢", type_id)
        panel = SettingsPanel()
        try:
            for table, column in ((panel.type_table, 2), (panel.device_table, 3)):
                action_cell = table.cellWidget(0, column)
                layout = action_cell.layout()
                margins = layout.contentsMargins()
                self.assertTrue(layout.alignment() & Qt.AlignmentFlag.AlignVCenter)
                self.assertEqual(margins.top(), 2)
                self.assertLessEqual(margins.bottom(), 2)

                for frame in action_cell.findChildren(QFrame):
                    if frame.objectName().startswith("settingsAction"):
                        self.assertEqual(frame.width(), 54)
                        self.assertEqual(frame.height(), 25)
                        self.assertGreaterEqual(table.rowHeight(0) - frame.height(), 21)
                        self.assertLessEqual(table.rowHeight(0) - frame.height(), 21)
        finally:
            panel.deleteLater()

    def test_settings_action_buttons_use_outer_frames_for_complete_borders(self):
        panel = SettingsPanel()
        try:
            action_cell = panel.type_table.cellWidget(0, 2)
            frames = [
                frame
                for frame in action_cell.findChildren(QFrame)
                if frame.objectName().startswith("settingsAction")
            ]

            self.assertEqual(len(frames), 2)
            for frame in frames:
                self.assertEqual(frame.width(), 54)
                self.assertEqual(frame.height(), 25)
                self.assertIn("border: 1px solid", frame.styleSheet())
                self.assertIn("border-radius: 5px", frame.styleSheet())
                self.assertEqual(len(frame.findChildren(QPushButton)), 1)
        finally:
            panel.deleteLater()

    def test_settings_action_cells_are_transparent_when_row_is_selected(self):
        type_id = db.add_device_type("测试类型")
        db.add_device("测试包厢", type_id)
        panel = SettingsPanel()
        try:
            for table, column in ((panel.type_table, 2), (panel.device_table, 3)):
                action_cell = table.cellWidget(0, column)

                self.assertTrue(
                    action_cell.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                )
                self.assertFalse(action_cell.autoFillBackground())
                self.assertIn("background: transparent", action_cell.styleSheet())
                self.assertIn("border: none", action_cell.styleSheet())
        finally:
            panel.deleteLater()

    def test_settings_tables_do_not_draw_focus_boxes_when_selected(self):
        panel = SettingsPanel()
        try:
            for table in (panel.type_table, panel.device_table):
                self.assertEqual(table.focusPolicy(), Qt.FocusPolicy.NoFocus)
                self.assertIn("QTableWidget::item:focus", table.styleSheet())
                self.assertIn("outline: 0", table.styleSheet())
                self.assertIn("border: none", table.styleSheet())

            action_cell = panel.type_table.cellWidget(0, 2)
            self.assertEqual(action_cell.focusPolicy(), Qt.FocusPolicy.NoFocus)
            for frame in action_cell.findChildren(QFrame):
                if frame.objectName().startswith("settingsAction"):
                    self.assertEqual(frame.focusPolicy(), Qt.FocusPolicy.NoFocus)
            for button in action_cell.findChildren(QPushButton):
                self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.NoFocus)
        finally:
            panel.deleteLater()

    def test_settings_tables_use_dark_custom_scrollbars(self):
        panel = SettingsPanel()
        try:
            for table in (panel.type_table, panel.device_table):
                table_style = table.styleSheet()

                self.assertIn("QTableWidget QScrollBar:vertical", table_style)
                self.assertIn("QTableWidget QScrollBar::handle:vertical", table_style)
                self.assertIn("QTableWidget QScrollBar:horizontal", table_style)
                self.assertIn("QTableWidget QTableCornerButton::section", table_style)
                self.assertIn("width: 12px", table_style)
                self.assertIn("height: 12px", table_style)
                self.assertIn("background: #111821", table_style)
                self.assertIn("background: #243040", table_style)
                self.assertIn("background: #80F7FF", table_style)
                self.assertIn("height: 0", table_style)
                self.assertIn("width: 0", table_style)
        finally:
            panel.deleteLater()

    def test_device_type_name_can_be_edited_from_left_panel_dialog(self):
        type_id = db.add_device_type("旧类型")
        panel = SettingsPanel()
        try:
            panel._type_edit_dialog_factory = lambda *_: FakeTypeEditDialog("新类型")

            panel._begin_edit_type(type_id, "旧类型")

            names = [row["name"] for row in db.get_all_device_types()]
            self.assertIn("新类型", names)
            self.assertNotIn("旧类型", names)
            self.assertIsNone(panel._editing_type_id)
            self.assertEqual(panel._type_submit_btn.text(), "新增类型")
            self.assertFalse(panel._type_cancel_btn.isVisible())
        finally:
            panel.deleteLater()

    def test_device_name_and_type_can_be_edited_from_right_panel_dialog(self):
        old_type_id = db.add_device_type("旧分区")
        new_type_id = db.add_device_type("新分区")
        device_id = db.add_device("旧包厢", old_type_id)
        panel = SettingsPanel()
        try:
            panel._device_edit_dialog_factory = (
                lambda *_: FakeDeviceEditDialog("新包厢", new_type_id)
            )

            panel._begin_edit_device(device_id, "旧包厢", old_type_id)

            device = db.get_device_by_id(device_id)
            self.assertEqual(device["name"], "新包厢")
            self.assertEqual(device["device_type_id"], new_type_id)
            self.assertEqual(device["type_name"], "新分区")
            self.assertIsNone(panel._editing_device_id)
            self.assertEqual(panel._device_submit_btn.text(), "新增包厢")
            self.assertFalse(panel._device_cancel_btn.isVisible())
        finally:
            panel.deleteLater()

    def test_device_edit_dialog_shows_field_labels(self):
        dialog = _DeviceEditDialog(
            "小包1",
            1,
            [{"id": 1, "name": "小包"}, {"id": 2, "name": "大包"}],
        )
        try:
            name_label = dialog.findChild(QLabel, "deviceNameFieldLabel")
            type_label = dialog.findChild(QLabel, "deviceTypeMappingFieldLabel")

            self.assertIsNotNone(name_label)
            self.assertIsNotNone(type_label)
            self.assertEqual(name_label.text(), "包厢名称")
            self.assertEqual(type_label.text(), "类型映射")
            self.assertIn("#B9C6D3", name_label.styleSheet())
            self.assertIn("#B9C6D3", type_label.styleSheet())
        finally:
            dialog.deleteLater()

    def test_delete_confirmation_dialog_uses_dark_settings_style(self):
        panel = SettingsPanel()
        try:
            dialog = panel._make_delete_confirm_dialog("确认删除", "删除这条记录？")

            self.assertIn("#0B1118", dialog.styleSheet())
            self.assertIn("#111821", dialog.styleSheet())
            button_texts = [button.text() for button in dialog.findChildren(QPushButton)]
            self.assertIn("取消", button_texts)
            self.assertIn("确认删除", button_texts)
        finally:
            panel.deleteLater()

    def test_empty_type_name_uses_themed_warning_dialog(self):
        panel = SettingsPanel()
        calls = []
        original_show_warning = settings_module.show_warning
        settings_module.show_warning = (
            lambda parent, title, message: calls.append((parent, title, message))
        )
        try:
            panel.type_name_input.clear()

            panel._on_type_submit()

            self.assertEqual(calls, [(panel, "输入错误", "请输入包厢类型名称。")])
        finally:
            settings_module.show_warning = original_show_warning
            panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
