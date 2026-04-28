"""
电玩店包厢计时系统 - 程序入口（v2）
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from database.db_manager import init_db, migrate_db
from ui.main_window import MainWindow
from config import APP_ICON_PATH, APP_NAME


def main():
    # 初始化数据库（创建表）
    init_db()
    # 迁移旧版本数据库（安全升级）
    migrate_db()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app_icon = QIcon(APP_ICON_PATH)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
