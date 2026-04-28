import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QLabel

from config import APP_ICON_PATH
from ui.main_window import MainWindow


class MainWindowNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_settings_is_embedded_as_third_stack_page(self):
        self.assertEqual(self.window._stack.count(), 3)

        self.window._switch_page(2)

        self.assertIs(self.window._stack.currentWidget(), self.window._settings_panel)

    def test_main_window_uses_custom_titlebar_icon(self):
        self.assertTrue(Path(APP_ICON_PATH).is_file())
        self.assertFalse(self.window.windowIcon().isNull())

    def test_pyinstaller_spec_uses_windows_exe_icon(self):
        icon_path = Path("assets/app_icon.ico")
        spec_text = Path("电玩计时.spec").read_text(encoding="utf-8")

        self.assertTrue(icon_path.is_file())
        self.assertIn("icon='assets/app_icon.ico'", spec_text)

    def test_app_icon_is_simplified_for_taskbar_sizes(self):
        png_path = Path(APP_ICON_PATH)
        icon = QIcon("assets/app_icon.ico")
        available_sizes = {(size.width(), size.height()) for size in icon.availableSizes()}

        self.assertLess(png_path.stat().st_size, 250_000)
        for size in (16, 24, 32, 48, 64, 256):
            self.assertIn((size, size), available_sizes)

    def test_pyinstaller_spec_bundles_runtime_image_assets(self):
        spec_text = Path("电玩计时.spec").read_text(encoding="utf-8")
        bundled_assets = {
            "assets/button_check.svg": "assets",
            "assets/button_play.svg": "assets",
            "assets/checkbox_checked.svg": "assets",
            "assets/dropdown_arrow.png": "assets",
            "assets/spinbox_arrow_down.png": "assets",
            "assets/spinbox_arrow_up.png": "assets",
            "assets/generated/nav_console.png": "assets/generated",
            "assets/generated/nav_settings.png": "assets/generated",
            "assets/generated/nav_stats.png": "assets/generated",
        }

        for asset_path, bundle_dir in bundled_assets.items():
            self.assertTrue(Path(asset_path).is_file())
            self.assertIn(f"('{asset_path}', '{bundle_dir}')", spec_text)

    def test_sidebar_brand_uses_local_arcade_name(self):
        label_texts = [label.text() for label in self.window.findChildren(QLabel)]

        self.assertIn("江城电玩", label_texts)
        self.assertNotIn("VG TIMER", label_texts)
        self.assertNotIn("LOCAL OPERATIONS", label_texts)

    def test_sidebar_navigation_uses_generated_icons(self):
        nav_buttons = [
            self.window._nav_device_btn,
            self.window._nav_stats_btn,
            self.window._nav_settings_btn,
        ]

        for button in nav_buttons:
            self.assertFalse(button.icon().isNull())
            self.assertEqual(button.iconSize(), QSize(26, 26))
            self.assertEqual(button.height(), 48)
            self.assertIn("font-size: 15px", button.styleSheet())

    def test_blank_navigation_and_page_surfaces_use_arrow_cursor(self):
        self.assertEqual(self.window.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertEqual(self.window._central.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertEqual(self.window._sidebar.cursor().shape(), Qt.CursorShape.ArrowCursor)
        self.assertEqual(self.window._stack.cursor().shape(), Qt.CursorShape.ArrowCursor)

        for page in (
            self.window._device_panel,
            self.window._stats_panel,
            self.window._settings_panel,
        ):
            self.assertEqual(page.cursor().shape(), Qt.CursorShape.ArrowCursor)


if __name__ == "__main__":
    unittest.main()
