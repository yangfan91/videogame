"""System settings page used inside the main window and legacy dialog wrapper."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import COLORS, DeviceStatus, is_dark_theme
from database import db_manager as db
from ui.message_box import show_warning
from ui.window_chrome import apply_dark_title_bar


class _SettingsEditDialog(QDialog):
    """Dark modal editor shared by settings edit flows."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setStyleSheet(self._dialog_style())
        apply_dark_title_bar(self)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 20, 20, 18)
        self._root.setSpacing(16)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 20px; font-weight: 900;"
        )
        self._root.addWidget(title_label)

    def _make_field_label(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label_color = "#B9C6D3" if is_dark_theme() else COLORS["text_muted"]
        label.setStyleSheet(
            f"color: {label_color}; font-size: 12px; font-weight: 800;"
        )
        return label

    def _add_actions(self):
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(86)
        cancel_btn.setStyleSheet(self._ghost_button_style())
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存修改")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(36)
        save_btn.setMinimumWidth(96)
        save_btn.setStyleSheet(self._primary_button_style())
        save_btn.clicked.connect(self.accept)

        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        self._root.addLayout(actions)

    def _dialog_style(self) -> str:
        return f"""
            QDialog {{
                background: {COLORS['background']};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLineEdit, QComboBox {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 13px;
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 26px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['surface_alt']};
            }}
        """

    def _primary_button_style(self) -> str:
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
                background: {COLORS['accent']};
            }}
        """

    def _ghost_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """


class _TypeEditDialog(_SettingsEditDialog):
    def __init__(self, name: str, parent=None):
        super().__init__("修改包厢类型", parent)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入类型名称")
        self.name_input.setText(name)
        self.name_input.setFixedHeight(42)
        self._root.addWidget(self.name_input)
        self._add_actions()
        self.name_input.selectAll()
        self.name_input.setFocus()

    @property
    def name(self) -> str:
        return self.name_input.text().strip()


class _DeviceEditDialog(_SettingsEditDialog):
    def __init__(self, name: str, type_id: int, device_types, parent=None):
        super().__init__("修改包厢", parent)

        self._type_ids: list[int] = []

        self._root.addWidget(
            self._make_field_label("包厢名称", "deviceNameFieldLabel")
        )
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入包厢名称")
        self.name_input.setText(name)
        self.name_input.setFixedHeight(42)
        self._root.addWidget(self.name_input)

        self._root.addWidget(
            self._make_field_label("类型映射", "deviceTypeMappingFieldLabel")
        )
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(42)
        for device_type in device_types:
            self.type_combo.addItem(device_type["name"])
            self._type_ids.append(int(device_type["id"]))
        if type_id in self._type_ids:
            self.type_combo.setCurrentIndex(self._type_ids.index(type_id))
        self._root.addWidget(self.type_combo)

        self._add_actions()
        self.name_input.selectAll()
        self.name_input.setFocus()

    @property
    def name(self) -> str:
        return self.name_input.text().strip()

    @property
    def type_id(self) -> int | None:
        index = self.type_combo.currentIndex()
        if 0 <= index < len(self._type_ids):
            return self._type_ids[index]
        return None


class SettingsPanel(QWidget):
    """Two-column settings console for room types and rooms."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None, show_header: bool = True):
        super().__init__(parent)
        self._show_header = show_header
        self._editing_type_id: int | None = None
        self._editing_device_id: int | None = None
        self._combo_type_ids: list[int] = []
        self._type_edit_dialog_factory = self._create_type_edit_dialog
        self._device_edit_dialog_factory = self._create_device_edit_dialog
        self.setObjectName("settingsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self._root_style())
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._init_ui()
        self._load_data()

    def refresh(self):
        self._load_data()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 30, 32, 30) if self._show_header else root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(22)

        if self._show_header:
            root.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(22)

        self._type_panel = self._build_type_panel()
        self._device_panel = self._build_device_panel()
        body.addWidget(self._type_panel)
        body.addWidget(self._device_panel, 1)
        root.addLayout(body, 1)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        title = QLabel("系统设置")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {COLORS['text_dark']};"
        )
        subtitle = QLabel("维护包厢类型、名称映射与基础状态，保持前台数据整洁一致。")
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {COLORS['text_muted']};"
        )

        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()
        return header

    def _build_type_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("settingsTypePanel")
        panel.setMinimumWidth(360)
        panel.setMaximumWidth(380)
        panel.setStyleSheet(self._panel_style("settingsTypePanel"))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        layout.addLayout(self._panel_title("包厢类型管理"))

        form = QHBoxLayout()
        form.setSpacing(10)
        self.type_name_input = QLineEdit()
        self.type_name_input.setPlaceholderText("输入类型名称")
        self.type_name_input.setFixedHeight(40)

        self._type_submit_btn = QPushButton("新增类型")
        self._type_submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._type_submit_btn.setFixedHeight(40)
        self._type_submit_btn.setStyleSheet(self._primary_button_style())
        self._type_submit_btn.clicked.connect(self._on_type_submit)

        form.addWidget(self.type_name_input, 1)
        form.addWidget(self._type_submit_btn)
        layout.addLayout(form)

        self._type_cancel_btn = QPushButton("取消修改")
        self._type_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._type_cancel_btn.setFixedHeight(34)
        self._type_cancel_btn.setStyleSheet(self._ghost_button_style())
        self._type_cancel_btn.clicked.connect(self._cancel_type_edit)
        self._type_cancel_btn.setVisible(False)
        layout.addWidget(self._type_cancel_btn)

        self.type_table = QTableWidget()
        self.type_table.setColumnCount(3)
        self.type_table.setHorizontalHeaderLabels(["类型名称", "包厢数", "操作"])
        self.type_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.type_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.type_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.type_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.type_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.type_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.type_table.setColumnWidth(1, 66)
        self.type_table.setColumnWidth(2, 132)
        self.type_table.verticalHeader().setVisible(False)
        self.type_table.setStyleSheet(self._table_style())
        layout.addWidget(self.type_table, 1)
        return panel

    def _build_device_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("settingsDevicePanel")
        panel.setStyleSheet(self._panel_style("settingsDevicePanel"))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title_row = QHBoxLayout()
        title_row.addLayout(self._panel_title("包厢名称设置"))
        title_row.addStretch()
        layout.addLayout(title_row)

        form = QHBoxLayout()
        form.setSpacing(10)
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("输入包厢名称")
        self.device_name_input.setFixedHeight(40)

        self.device_type_combo = QComboBox()
        self.device_type_combo.setFixedHeight(40)
        self.device_type_combo.setMinimumWidth(180)

        self._device_submit_btn = QPushButton("新增包厢")
        self._device_submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._device_submit_btn.setFixedHeight(40)
        self._device_submit_btn.setStyleSheet(self._primary_button_style())
        self._device_submit_btn.clicked.connect(self._on_device_submit)

        form.addWidget(self.device_name_input, 1)
        form.addWidget(self.device_type_combo)
        form.addWidget(self._device_submit_btn)
        layout.addLayout(form)

        self._device_cancel_btn = QPushButton("取消修改")
        self._device_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._device_cancel_btn.setFixedHeight(34)
        self._device_cancel_btn.setStyleSheet(self._ghost_button_style())
        self._device_cancel_btn.clicked.connect(self._cancel_device_edit)
        self._device_cancel_btn.setVisible(False)
        layout.addWidget(self._device_cancel_btn)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(4)
        self.device_table.setHorizontalHeaderLabels(["包厢名称", "类型映射", "状态", "操作"])
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.device_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.device_table.setColumnWidth(2, 110)
        self.device_table.setColumnWidth(3, 132)
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.setStyleSheet(self._table_style())
        layout.addWidget(self.device_table, 1)
        return panel

    def _panel_title(self, title: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(0)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 20px; font-weight: 900;"
        )
        layout.addWidget(title_label)
        return layout

    def _load_data(self):
        self._load_device_types()
        self._load_devices()

    def _load_device_types(self):
        types = db.get_all_device_types()
        counts = self._device_counts_by_type()
        self.type_table.setRowCount(len(types))
        self._type_ids = []

        for row, device_type in enumerate(types):
            self.type_table.setRowHeight(row, 46)
            type_id = int(device_type["id"])
            name = device_type["name"]
            self._type_ids.append(type_id)
            self.type_table.setItem(row, 0, self._make_item(name, align_left=True))
            self.type_table.setItem(row, 1, self._make_item(str(counts.get(type_id, 0))))
            self.type_table.setCellWidget(
                row,
                2,
                self._action_cell(
                    lambda checked=False, t=type_id, n=name: self._begin_edit_type(t, n),
                    lambda checked=False, t=type_id: self._delete_device_type(t),
                ),
            )

        self._refresh_type_combo()

    def _load_devices(self):
        devices = db.get_all_devices()
        self.device_table.setRowCount(len(devices))
        self._device_ids = []

        for row, device in enumerate(devices):
            self.device_table.setRowHeight(row, 46)
            device_id = int(device["id"])
            type_id = int(device["device_type_id"])
            self._device_ids.append(device_id)
            self.device_table.setItem(row, 0, self._make_item(device["name"], align_left=True))
            self.device_table.setItem(row, 1, self._make_item(device["type_name"], align_left=True))
            self.device_table.setItem(row, 2, self._make_item(DeviceStatus.LABELS.get(device["status"], device["status"])))
            self.device_table.setCellWidget(
                row,
                3,
                self._action_cell(
                    lambda checked=False, d=device_id, n=device["name"], t=type_id: self._begin_edit_device(d, n, t),
                    lambda checked=False, d=device_id: self._delete_device(d),
                ),
            )

    def _device_counts_by_type(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for device in db.get_all_devices():
            type_id = int(device["device_type_id"])
            counts[type_id] = counts.get(type_id, 0) + 1
        return counts

    def _refresh_type_combo(self):
        current_type_id = self._current_combo_type_id()
        self.device_type_combo.clear()
        self._combo_type_ids = []
        for device_type in db.get_all_device_types():
            self.device_type_combo.addItem(device_type["name"])
            self._combo_type_ids.append(int(device_type["id"]))
        if current_type_id is not None:
            self._set_combo_to_type_id(current_type_id)

    def _current_combo_type_id(self) -> int | None:
        idx = self.device_type_combo.currentIndex()
        if 0 <= idx < len(self._combo_type_ids):
            return self._combo_type_ids[idx]
        return None

    def _set_combo_to_type_id(self, type_id: int) -> bool:
        if type_id not in self._combo_type_ids:
            return False
        self.device_type_combo.setCurrentIndex(self._combo_type_ids.index(type_id))
        return True

    def _on_type_submit(self):
        name = self.type_name_input.text().strip()
        if not name:
            show_warning(self, "输入错误", "请输入包厢类型名称。")
            return
        try:
            if self._editing_type_id is None:
                db.add_device_type(name)
            else:
                db.update_device_type(self._editing_type_id, name)
            self._cancel_type_edit(clear_text=True)
            self._load_data()
            self.settings_changed.emit()
        except Exception as exc:
            show_warning(self, "保存失败", f"包厢类型保存失败：{exc}")

    def _begin_edit_type(self, type_id: int, name: str):
        dialog = self._type_edit_dialog_factory(name)
        if not dialog.exec():
            return

        new_name = dialog.name.strip()
        if not new_name:
            show_warning(self, "输入错误", "请输入包厢类型名称。")
            return

        try:
            db.update_device_type(type_id, new_name)
            self._editing_type_id = None
            self._type_submit_btn.setText("新增类型")
            self._type_cancel_btn.setVisible(False)
            self._load_data()
            self.settings_changed.emit()
        except Exception as exc:
            show_warning(self, "保存失败", f"包厢类型保存失败：{exc}")

    def _cancel_type_edit(self, clear_text: bool = True):
        self._editing_type_id = None
        if clear_text:
            self.type_name_input.clear()
        self._type_submit_btn.setText("新增类型")
        self._type_cancel_btn.setVisible(False)

    def _on_device_submit(self):
        name = self.device_name_input.text().strip()
        type_id = self._current_combo_type_id()
        if not name:
            show_warning(self, "输入错误", "请输入包厢名称。")
            return
        if type_id is None:
            show_warning(self, "输入错误", "请选择包厢类型。")
            return
        try:
            if self._editing_device_id is None:
                db.add_device(name, type_id)
            else:
                db.update_device(self._editing_device_id, name, type_id)
            self._cancel_device_edit(clear_text=True)
            self._load_data()
            self.settings_changed.emit()
        except Exception as exc:
            show_warning(self, "保存失败", f"包厢保存失败：{exc}")

    def _begin_edit_device(self, device_id: int, name: str, type_id: int):
        dialog = self._device_edit_dialog_factory(name, type_id, db.get_all_device_types())
        if not dialog.exec():
            return

        new_name = dialog.name.strip()
        new_type_id = dialog.type_id
        if not new_name:
            show_warning(self, "输入错误", "请输入包厢名称。")
            return
        if new_type_id is None:
            show_warning(self, "输入错误", "请选择包厢类型。")
            return

        try:
            db.update_device(device_id, new_name, new_type_id)
            self._editing_device_id = None
            self._device_submit_btn.setText("新增包厢")
            self._device_cancel_btn.setVisible(False)
            self._load_data()
            self.settings_changed.emit()
        except Exception as exc:
            show_warning(self, "保存失败", f"包厢保存失败：{exc}")

    def _cancel_device_edit(self, clear_text: bool = True):
        self._editing_device_id = None
        if clear_text:
            self.device_name_input.clear()
        self._device_submit_btn.setText("新增包厢")
        self._device_cancel_btn.setVisible(False)

    def _delete_device_type(self, type_id: int):
        if self._confirm_delete(
            "确认删除",
            "确定要删除此包厢类型吗？已关联包厢可能无法正常显示。",
        ):
            db.delete_device_type(type_id)
            self._load_data()
            self.settings_changed.emit()

    def _delete_device(self, device_id: int):
        if self._confirm_delete(
            "确认删除",
            "确定要删除此包厢吗？历史记录会保留。",
        ):
            db.delete_device(device_id)
            self._load_data()
            self.settings_changed.emit()

    def _create_type_edit_dialog(self, name: str):
        return _TypeEditDialog(name, self)

    def _create_device_edit_dialog(self, name: str, type_id: int, device_types):
        return _DeviceEditDialog(name, type_id, device_types, self)

    def _confirm_delete(self, title: str, message: str) -> bool:
        return bool(self._make_delete_confirm_dialog(title, message).exec())

    def _make_delete_confirm_dialog(self, title: str, message: str) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setMinimumWidth(380)
        dialog.setStyleSheet(f"""
            QDialog {{
                background: {COLORS['background']};
            }}
            QFrame#settingsConfirmCard {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        apply_dark_title_bar(dialog)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("settingsConfirmCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 18)
        card_layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 20px; font-weight: 900;"
        )
        card_layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #B9C6D3; font-size: 13px; line-height: 18px;")
        card_layout.addWidget(message_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(86)
        cancel_btn.setStyleSheet(self._ghost_button_style())
        cancel_btn.clicked.connect(dialog.reject)
        actions.addWidget(cancel_btn)

        delete_btn = QPushButton("确认删除")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setFixedHeight(36)
        delete_btn.setMinimumWidth(96)
        delete_btn.setStyleSheet(self._danger_button_style())
        delete_btn.clicked.connect(dialog.accept)
        actions.addWidget(delete_btn)

        card_layout.addLayout(actions)
        root.addWidget(card)
        return dialog

    def _make_item(self, text: str, align_left: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        alignment = Qt.AlignmentFlag.AlignVCenter
        alignment |= Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignCenter
        item.setTextAlignment(alignment)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _action_cell(self, edit_callback, delete_callback) -> QWidget:
        cell = QWidget()
        cell.setObjectName("settingsActionCell")
        cell.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        cell.setAutoFillBackground(False)
        cell.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cell.setStyleSheet("""
            QWidget#settingsActionCell {
                background: transparent;
                border: none;
            }
        """)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(
            self._framed_action_button(
                "修改",
                "settingsActionEditFrame",
                self._action_edit_frame_style(),
                self._action_text_button_style(COLORS["text_dark"], COLORS["accent"]),
                edit_callback,
            )
        )
        layout.addWidget(
            self._framed_action_button(
                "删除",
                "settingsActionDeleteFrame",
                self._action_delete_frame_style(),
                self._action_text_button_style("#FF7A90", "#FFA1B0"),
                delete_callback,
            )
        )
        return cell

    def _framed_action_button(
        self,
        text: str,
        object_name: str,
        frame_style: str,
        button_style: str,
        callback,
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        frame.setFixedSize(54, 25)
        frame.setStyleSheet(frame_style)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setFixedSize(54, 25)
        button.setStyleSheet(button_style)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return frame

    def _action_edit_frame_style(self) -> str:
        return f"""
            QFrame#settingsActionEditFrame {{
                background: {COLORS['surface_alt']};
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
            }}
        """

    def _action_delete_frame_style(self) -> str:
        return """
            QFrame#settingsActionDeleteFrame {
                background: #2A1721;
                border: 1px solid #563041;
                border-radius: 5px;
            }
        """

    def _action_text_button_style(self, color: str, hover_color: str) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: none;
                font-size: 11px;
                font-weight: 800;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {hover_color};
            }}
        """

    def _root_style(self) -> str:
        return f"""
            QWidget#settingsPanel {{
                background-color: {COLORS['background']};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLineEdit, QComboBox {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 26px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['surface_alt']};
            }}
        """

    def _panel_style(self, object_name: str) -> str:
        return f"""
            QFrame#{object_name} {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QFrame#{object_name} QLabel {{
                background: transparent;
                border: none;
            }}
        """

    def _primary_button_style(self) -> str:
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
                background: {COLORS['accent']};
            }}
        """

    def _ghost_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """

    def _danger_button_style(self) -> str:
        return """
            QPushButton {
                background: #2A1721;
                color: #FF7A90;
                border: 1px solid #563041;
                border-radius: 7px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #FF7A90;
                background: #361A29;
            }
        """

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{
                background: {COLORS['surface']};
                alternate-background-color: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border_soft']};
                font-size: 12px;
            }}
            QHeaderView::section {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_muted']};
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 8px;
                font-size: 11px;
                font-weight: 900;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border_soft']};
            }}
            QTableWidget::item:selected {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_dark']};
            }}
            QTableWidget::item:focus {{
                border: none;
                outline: 0;
            }}
            QTableWidget QTableCornerButton::section {{
                background: {COLORS['surface_alt']};
                border: none;
            }}
            QTableWidget QScrollBar:vertical {{
                background: {COLORS['card_bg']};
                width: 12px;
                margin: 3px 2px 3px 0;
                border: none;
            }}
            QTableWidget QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-height: 42px;
            }}
            QTableWidget QScrollBar::handle:vertical:hover {{
                background: #2F4358;
            }}
            QTableWidget QScrollBar::handle:vertical:pressed {{
                background: {COLORS['accent']};
            }}
            QTableWidget QScrollBar::add-line:vertical,
            QTableWidget QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
                border: none;
            }}
            QTableWidget QScrollBar::add-page:vertical,
            QTableWidget QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QTableWidget QScrollBar:horizontal {{
                background: {COLORS['card_bg']};
                height: 12px;
                margin: 0 3px 2px 3px;
                border: none;
            }}
            QTableWidget QScrollBar::handle:horizontal {{
                background: {COLORS['border']};
                border-radius: 5px;
                min-width: 42px;
            }}
            QTableWidget QScrollBar::handle:horizontal:hover {{
                background: #2F4358;
            }}
            QTableWidget QScrollBar::handle:horizontal:pressed {{
                background: {COLORS['accent']};
            }}
            QTableWidget QScrollBar::add-line:horizontal,
            QTableWidget QScrollBar::sub-line:horizontal {{
                width: 0;
                background: transparent;
                border: none;
            }}
            QTableWidget QScrollBar::add-page:horizontal,
            QTableWidget QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """


class SettingsDialog(QDialog):
    """Compatibility wrapper for legacy callers that still open settings as a dialog."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("包厢系统设置")
        self.setMinimumSize(980, 640)
        self.setModal(True)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['background']}; }}")
        apply_dark_title_bar(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.panel = SettingsPanel(self, show_header=False)
        self.panel.settings_changed.connect(self.settings_changed)
        layout.addWidget(self.panel, 1)

        btn_bar = QFrame()
        btn_bar.setObjectName("dialogButtonBar")
        btn_bar.setStyleSheet(
            f"QFrame#dialogButtonBar {{ background: {COLORS['card_bg']}; border-top: 1px solid {COLORS['border']}; }}"
        )
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 12, 16, 12)
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(self.panel._primary_button_style())
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addWidget(btn_bar)
