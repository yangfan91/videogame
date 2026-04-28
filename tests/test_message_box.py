import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from config import COLORS
from ui.message_box import make_message_dialog


class ThemedMessageBoxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_warning_dialog_uses_dark_app_style_with_readable_text(self):
        dialog = make_message_dialog(
            None,
            "输入错误",
            "请输入包厢类型名称。",
            tone="warning",
        )
        try:
            style = dialog.styleSheet()
            labels = {label.text(): label for label in dialog.findChildren(QLabel)}
            buttons = [button for button in dialog.findChildren(QPushButton)]

            self.assertIs(dialog.property("usesDarkTitleBar"), True)
            self.assertIn(COLORS["background"], style)
            self.assertIn(COLORS["card_bg"], style)
            self.assertIn(COLORS["border"], style)
            self.assertIn("输入错误", labels)
            self.assertIn("请输入包厢类型名称。", labels)
            self.assertIn(f"color: {COLORS['text_dark']}", labels["输入错误"].styleSheet())
            self.assertIn("#DCE8F2", labels["请输入包厢类型名称。"].styleSheet())
            self.assertIn("font-size: 14px", labels["请输入包厢类型名称。"].styleSheet())
            self.assertIn("确定", [button.text() for button in buttons])
            self.assertNotIn("OK", [button.text() for button in buttons])
            self.assertTrue(all(button.height() >= 36 for button in buttons))
            self.assertTrue(any(COLORS["accent"] in button.styleSheet() for button in buttons))
        finally:
            dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
