"""
统计报表面板。
"""
from pathlib import Path

from PyQt6.QtCore import QDate, QEvent, QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import ASSETS_DIR, COLORS, TimerMode
from core.billing import format_duration
from database import db_manager as db
from ui.message_box import show_warning

DATE_DROPDOWN_ARROW_ICON = Path(ASSETS_DIR, "dropdown_arrow.png").as_posix()
SPINBOX_ARROW_UP_ICON = Path(ASSETS_DIR, "spinbox_arrow_up.png").as_posix()
SPINBOX_ARROW_DOWN_ICON = Path(ASSETS_DIR, "spinbox_arrow_down.png").as_posix()


class _MetricCard(QFrame):
    """Small summary card that can emit its key on click."""

    clicked = pyqtSignal(str)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.metric_key = key

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.metric_key)
        super().mousePressEvent(event)


class _YearStepperOverlay(QObject):
    """Visible year steppers for QCalendarWidget's compact year editor."""

    def __init__(self, spinbox: QSpinBox):
        super().__init__(spinbox)
        self.spinbox = spinbox
        self.up_button = self._make_button(
            "calendarYearStepUpButton",
            SPINBOX_ARROW_UP_ICON,
            spinbox.stepUp,
        )
        self.down_button = self._make_button(
            "calendarYearStepDownButton",
            SPINBOX_ARROW_DOWN_ICON,
            spinbox.stepDown,
        )
        spinbox.installEventFilter(self)
        self.update_geometry()

    def _make_button(self, object_name: str, icon_path: str, callback) -> QToolButton:
        button = QToolButton(self.spinbox)
        button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIcon(QIcon(icon_path))
        button.setIconSize(QSize(10, 7))
        button.setAutoRaise(False)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(callback)
        button.setStyleSheet(
            f"""
            QToolButton#{object_name} {{
                background: {COLORS['surface_alt']};
                border: none;
                border-left: 1px solid {COLORS['border']};
                padding: 0;
            }}
            QToolButton#{object_name}:hover {{
                background: #1E3A46;
            }}
            QToolButton#{object_name}:pressed {{
                background: #245C66;
            }}
            """
        )
        return button

    def eventFilter(self, obj, event):  # noqa: N802 - Qt API name
        if obj is self.spinbox and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Polish,
        ):
            self.update_geometry()
        return False

    def update_geometry(self):
        width = 24
        height = max(26, self.spinbox.height())
        half = max(12, height // 2)
        x = max(0, self.spinbox.width() - width - 1)
        self.up_button.setGeometry(x, 1, width, half)
        self.down_button.setGeometry(x, half, width, height - half - 1)
        self.up_button.raise_()
        self.down_button.raise_()
        self.up_button.show()
        self.down_button.show()


class StatsPanel(QWidget):
    """包厢统计报表面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating_history_table = False
        self._history_device_filter: str | None = None
        self._metric_filter_key: str | None = None
        self._history_records = []
        self._metric_cards: list[QFrame] = []
        self._metric_cards_by_key: dict[str, _MetricCard] = {}
        self._metric_values: dict[str, QLabel] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self.setStyleSheet(f"background: {COLORS['background']};")
        self.setCursor(Qt.CursorShape.ArrowCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(22)

        header = QHBoxLayout()
        header.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        title = QLabel("统计报表")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {COLORS['text_dark']};"
        )
        subtitle = QLabel("按日期区间查看场次、时长、支付与模式分布。")
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {COLORS['text_muted']};"
        )
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        header.addWidget(self._build_filter_bar())
        root.addLayout(header)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(14)
        metric_row.addWidget(self._make_metric_card("总场次", "0", COLORS["text_dark"], "total_count"))
        metric_row.addWidget(self._make_metric_card("总时长", "0h", COLORS["accent"], "total_hours"))
        metric_row.addWidget(
            self._make_metric_card(
                "团购套餐", "0", COLORS["countdown"], "countdown_count", filterable=True
            )
        )
        metric_row.addWidget(
            self._make_metric_card(
                "自由计时", "0", COLORS["secondary"], "freeplay_count", filterable=True
            )
        )
        metric_row.addWidget(
            self._make_metric_card("已支付", "0", COLORS["success"], "paid_count", filterable=True)
        )
        metric_row.addWidget(
            self._make_metric_card("未支付", "0", COLORS["danger"], "unpaid_count", filterable=True)
        )
        root.addLayout(metric_row)

        body = QVBoxLayout()
        body.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        left_col.addWidget(self._section_title("设备维度概览"))
        left_col.addWidget(self._build_device_table_card(), 1)
        left_col.addLayout(self._build_history_title_row())
        left_col.addWidget(self._build_history_table_card(), 1)
        body.addLayout(left_col, 1)

        root.addLayout(body, 1)

    def _build_filter_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("filterBar")
        frame.setStyleSheet(
            f"""
            QFrame#filterBar {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            """
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        for label, days in [("今日", 0), ("近7天", 6), ("本月", -1)]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(self._ghost_button_style())
            btn.clicked.connect(lambda checked=False, d=days: self._set_quick_date(d))
            layout.addWidget(btn)

        self.date_from = QDateEdit(QDate.currentDate())
        self.date_to = QDateEdit(QDate.currentDate())
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedHeight(30)
            edit.setMinimumWidth(132)
            edit.setStyleSheet(self._input_style())
            edit.calendarWidget().setStyleSheet(self._calendar_style())
            self._style_calendar_arrow_buttons(edit)
            self._configure_calendar_year_input(edit)

        layout.addWidget(self.date_from)
        separator = QLabel("至")
        separator.setObjectName("dateRangeSeparator")
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator.setMinimumWidth(24)
        separator.setStyleSheet(
            f"background: transparent; border: none; color: {COLORS['text_dark']}; "
            "font-size: 12px; font-weight: 700;"
        )
        layout.addWidget(separator)
        layout.addWidget(self.date_to)

        query_btn = QPushButton("查询")
        query_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        query_btn.setFixedHeight(30)
        query_btn.setStyleSheet(self._solid_button_style(COLORS["accent"]))
        query_btn.clicked.connect(self.refresh)
        layout.addWidget(query_btn)
        return frame

    def _build_device_table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        card.setStyleSheet(self._panel_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(
            ["设备", "类型", "场次", "总时长", "模式分布"]
        )
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setAlternatingRowColors(False)
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.verticalHeader().setDefaultSectionSize(42)
        self.device_table.verticalHeader().setMinimumSectionSize(40)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.device_table.horizontalHeader().setMinimumHeight(40)
        self.device_table.setStyleSheet(self._table_style())
        self.device_table.cellClicked.connect(self._on_device_row_clicked)
        layout.addWidget(self.device_table)
        return card

    def _build_history_title_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self._section_title("历史记录"))
        row.addStretch()

        self.history_all_btn = QPushButton("全部")
        self.history_all_btn.setObjectName("historyAllButton")
        self.history_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_all_btn.setFixedHeight(28)
        self.history_all_btn.setStyleSheet(self._ghost_button_style())
        self.history_all_btn.clicked.connect(self._clear_history_device_filter)
        row.addWidget(self.history_all_btn)
        return row

    def _build_history_table_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        card.setStyleSheet(self._panel_style())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels(
            ["包厢", "类型", "模式", "开始时间", "时长", "付款", "收款方式", "备注"]
        )
        self.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(42)
        self.history_table.verticalHeader().setMinimumSectionSize(40)
        self.history_table.horizontalHeader().setMinimumHeight(40)
        self._configure_history_table_columns()
        self.history_table.setStyleSheet(self._table_style())
        self.history_table.itemChanged.connect(self._on_history_item_changed)
        layout.addWidget(self.history_table)
        return card

    def _configure_history_table_columns(self):
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(72)
        widths = [128, 96, 110, 168, 96, 80, 120, 280]
        for column, width in enumerate(widths):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.history_table.setColumnWidth(column, width)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.history_table.setColumnWidth(7, widths[7])

    def _make_metric_card(
        self,
        title: str,
        value: str,
        value_color: str,
        key: str,
        filterable: bool = False,
    ) -> QFrame:
        card = _MetricCard(key)
        card.setObjectName("panelCard")
        card.setStyleSheet(self._metric_card_style(active=False))
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setFixedHeight(68)
        if filterable or key in {"total_count", "total_hours"}:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.clicked.connect(self._on_metric_card_clicked)
        self._metric_cards.append(card)
        self._metric_cards_by_key[key] = card

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500;"
        )
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {value_color}; font-size: 22px; font-weight: 700;"
        )
        self._metric_values[key] = value_lbl

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        layout.addStretch()
        return card

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {COLORS['text_dark']}; font-size: 16px; font-weight: 700;"
        )
        return label

    def refresh(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        data = db.get_stats_by_date(date_from, date_to)
        summary = data["summary"]
        records = data["records"]
        self._history_records = list(records)

        total_count = summary["total_count"] or 0
        total_seconds = summary["total_seconds"] or 0
        countdown_count = summary["countdown_count"] or 0
        freeplay_count = summary["freeplay_count"] or 0
        paid_count = summary["paid_count"] or 0
        unpaid_count = max(0, total_count - paid_count)
        total_hours = total_seconds / 3600 if total_seconds else 0

        self._metric_values["total_count"].setText(str(total_count))
        self._metric_values["total_hours"].setText(f"{total_hours:.1f}h")
        self._metric_values["countdown_count"].setText(str(countdown_count))
        self._metric_values["freeplay_count"].setText(str(freeplay_count))
        self._metric_values["paid_count"].setText(str(paid_count))
        self._metric_values["unpaid_count"].setText(str(unpaid_count))

        self._refresh_metric_card_styles()
        self._render_reports()

    def _render_reports(self):
        self._render_device_table(self._metric_filtered_records())
        self._render_history_table()

    def _render_device_table(self, records):
        by_device = self._device_rows_from_records(records)
        self.device_table.setRowCount(len(by_device))
        for row, device in enumerate(by_device):
            secs = device["total_seconds"] or 0
            cd = device["countdown_count"] or 0
            fp = device["freeplay_count"] or 0
            self._set_item(self.device_table, row, 0, device["device_name"])
            self._set_item(self.device_table, row, 1, device["type_name"])
            self._set_item(self.device_table, row, 2, str(device["session_count"]))
            self._set_item(self.device_table, row, 3, format_duration(secs))
            self._set_item(self.device_table, row, 4, f"团购 {cd} / 自由 {fp}")

    def _device_rows_from_records(self, records):
        grouped = {}
        for rec in records:
            key = (rec["device_name"], rec["type_name"])
            if key not in grouped:
                grouped[key] = {
                    "device_name": rec["device_name"],
                    "type_name": rec["type_name"],
                    "session_count": 0,
                    "total_seconds": 0,
                    "countdown_count": 0,
                    "freeplay_count": 0,
                }
            item = grouped[key]
            item["session_count"] += 1
            item["total_seconds"] += rec["total_seconds"] or 0
            if rec["timer_mode"] == TimerMode.COUNTDOWN:
                item["countdown_count"] += 1
            elif rec["timer_mode"] == TimerMode.FREEPLAY:
                item["freeplay_count"] += 1
        return sorted(
            grouped.values(),
            key=lambda item: (-item["total_seconds"], item["device_name"]),
        )

    def _metric_filtered_records(self):
        return [
            rec for rec in self._history_records
            if self._record_matches_metric_filter(rec)
        ]

    def _filtered_history_records(self):
        records = self._metric_filtered_records()
        if self._history_device_filter:
            records = [
                rec for rec in records
                if rec["device_name"] == self._history_device_filter
            ]
        return records

    def _record_matches_metric_filter(self, rec) -> bool:
        if self._metric_filter_key == "countdown_count":
            return rec["timer_mode"] == TimerMode.COUNTDOWN
        if self._metric_filter_key == "freeplay_count":
            return rec["timer_mode"] == TimerMode.FREEPLAY
        if self._metric_filter_key == "paid_count":
            return bool(rec["paid"])
        if self._metric_filter_key == "unpaid_count":
            return not bool(rec["paid"])
        return True

    def _render_history_table(self):
        records = self._filtered_history_records()
        self._updating_history_table = True
        self.history_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            secs = rec["total_seconds"] or 0
            mode_text = TimerMode.LABELS.get(rec["timer_mode"], rec["timer_mode"])
            paid_text = "已付" if rec["paid"] else "未付"
            payment_method = rec["payment_method"] or "—"

            self._set_item(self.history_table, row, 0, rec["device_name"])
            self._set_item(self.history_table, row, 1, rec["type_name"])
            self._set_item(self.history_table, row, 2, mode_text)
            self._set_item(self.history_table, row, 3, rec["start_time"])
            self._set_item(self.history_table, row, 4, format_duration(secs))

            paid_item = self._make_table_item(paid_text)
            paid_item.setForeground(
                QColor(COLORS["success"] if rec["paid"] else COLORS["warning"])
            )
            self.history_table.setItem(row, 5, paid_item)

            method_item = self._make_table_item(payment_method)
            method_item.setForeground(
                QColor(COLORS["text_dark"] if rec["payment_method"] else COLORS["text_muted"])
            )
            self.history_table.setItem(row, 6, method_item)

            note_item = self._make_table_item(rec["note"] or "", editable=True, align_left=True)
            note_item.setData(Qt.ItemDataRole.UserRole, rec["id"])
            self.history_table.setItem(row, 7, note_item)
        self._updating_history_table = False

    def _on_device_row_clicked(self, row: int, column: int):
        item = self.device_table.item(row, 0)
        if item is None:
            return
        self._history_device_filter = item.text()
        self._render_history_table()

    def _clear_history_device_filter(self):
        self._history_device_filter = None
        self._render_history_table()

    def _set_metric_filter(self, key: str):
        if key not in {"countdown_count", "freeplay_count", "paid_count", "unpaid_count"}:
            return
        self._metric_filter_key = key
        self._refresh_metric_card_styles()
        self._render_reports()

    def _on_metric_card_clicked(self, key: str):
        if key in {"total_count", "total_hours"}:
            self._clear_metric_filter()
            return
        self._set_metric_filter(key)

    def _clear_metric_filter(self):
        self._metric_filter_key = None
        self._refresh_metric_card_styles()
        self._render_reports()

    def _refresh_metric_card_styles(self):
        active_key = self._metric_filter_key or "total_count"
        for key, card in self._metric_cards_by_key.items():
            card.setStyleSheet(self._metric_card_style(active=key == active_key))

    def _set_quick_date(self, days: int):
        today = QDate.currentDate()
        if days == 0:
            self.date_from.setDate(today)
            self.date_to.setDate(today)
        elif days > 0:
            self.date_from.setDate(today.addDays(-days))
            self.date_to.setDate(today)
        else:
            first_day = QDate(today.year(), today.month(), 1)
            self.date_from.setDate(first_day)
            self.date_to.setDate(today)
        self.refresh()

    def _make_table_item(
        self, text: str, editable: bool = False, align_left: bool = False
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        alignment = Qt.AlignmentFlag.AlignVCenter
        alignment |= Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignCenter
        item.setTextAlignment(alignment)
        flags = item.flags()
        if editable:
            item.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(flags & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _set_item(self, table: QTableWidget, row: int, col: int, text: str):
        table.setItem(row, col, self._make_table_item(text))

    def _on_history_item_changed(self, item: QTableWidgetItem):
        if self._updating_history_table or item.column() != 7:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id is None:
            return
        if not db.update_session_note(int(session_id), item.text().strip()):
            self._updating_history_table = True
            show_warning(self, "保存失败", "备注保存失败，请重试。")
            self.refresh()
            self._updating_history_table = False

    def _ghost_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: {COLORS['accent']};
                color: {COLORS['accent']};
                background: {COLORS['card_bg']};
            }}
        """

    def _solid_button_style(self, color: str) -> str:
        text_color = COLORS["accent_text"] if color == COLORS["accent"] else "white"
        return f"""
            QPushButton {{
                background: {color};
                color: {text_color};
                border: none;
                border-radius: 7px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {color};
            }}
        """

    def _input_style(self) -> str:
        return f"""
            QDateEdit {{
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 12px;
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
            }}
            QDateEdit:focus {{
                border-color: {COLORS['accent']};
            }}
            QDateEdit::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 24px;
                margin: 1px 1px 1px 0;
                background: transparent;
                border: none;
            }}
            QDateEdit::down-arrow {{
                image: url({DATE_DROPDOWN_ARROW_ICON});
                width: 10px;
                height: 7px;
                margin-right: 7px;
            }}
        """

    def _calendar_style(self) -> str:
        return f"""
            QCalendarWidget {{
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['accent']};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border-bottom: 1px solid {COLORS['border']};
            }}
            QCalendarWidget QToolButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 700;
            }}
            QCalendarWidget QToolButton:hover {{
                background: {COLORS['surface_alt']};
                color: {COLORS['accent']};
            }}
            QCalendarWidget QMenu {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
            }}
            QCalendarWidget QSpinBox {{
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 2px 30px 2px 8px;
                min-width: 74px;
                min-height: 24px;
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
            }}
            QCalendarWidget QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 28px;
                height: 14px;
                background: {COLORS['surface_alt']};
                border-left: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
                border-top-right-radius: 4px;
            }}
            QCalendarWidget QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 28px;
                height: 14px;
                background: {COLORS['surface_alt']};
                border-left: 1px solid {COLORS['border']};
                border-bottom-right-radius: 4px;
            }}
            QCalendarWidget QSpinBox::up-button:hover,
            QCalendarWidget QSpinBox::down-button:hover {{
                background: #1E3A46;
            }}
            QCalendarWidget QSpinBox::up-arrow {{
                image: url({SPINBOX_ARROW_UP_ICON});
                width: 10px;
                height: 7px;
            }}
            QCalendarWidget QSpinBox::down-arrow {{
                image: url({SPINBOX_ARROW_DOWN_ICON});
                width: 10px;
                height: 7px;
            }}
            QCalendarWidget QAbstractItemView {{
                background: {COLORS['card_bg']};
                color: {COLORS['text_dark']};
                alternate-background-color: {COLORS['surface']};
                selection-background-color: {COLORS['accent']};
                selection-color: {COLORS['background']};
                outline: none;
            }}
            QCalendarWidget QAbstractItemView:item:hover {{
                background: {COLORS['surface_alt']};
                color: {COLORS['accent']};
            }}
        """

    def _style_calendar_arrow_buttons(self, edit: QDateEdit):
        arrows = {
            "qt_calendar_prevmonth": "‹",
            "qt_calendar_nextmonth": "›",
        }
        for object_name, text in arrows.items():
            button = edit.calendarWidget().findChild(QToolButton, object_name)
            if button is None:
                continue
            button.setIcon(QIcon())
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setStyleSheet(
                f"""
                QToolButton {{
                    background: {COLORS['surface']};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    font-size: 18px;
                    font-weight: 900;
                    padding: 0 8px;
                }}
                QToolButton:hover {{
                    background: {COLORS['surface_alt']};
                    color: #FFFFFF;
                }}
                """
            )

    def _configure_calendar_year_input(self, edit: QDateEdit):
        calendar = edit.calendarWidget()
        year_spinbox = calendar.findChild(QSpinBox, "qt_calendar_yearedit")
        if year_spinbox is None:
            return

        year_spinbox.setReadOnly(False)
        year_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        year_spinbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        year_spinbox.setKeyboardTracking(True)
        year_spinbox.setMinimumWidth(96)
        year_spinbox.setMinimumHeight(28)
        hints = Qt.InputMethodHint.ImhDigitsOnly | Qt.InputMethodHint.ImhPreferNumbers
        year_spinbox.setInputMethodHints(hints)

        line_edit = year_spinbox.lineEdit()
        line_edit.setReadOnly(False)
        line_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        line_edit.setInputMethodHints(hints)
        line_edit.setTextMargins(0, 0, 28, 0)
        line_edit.textEdited.connect(
            lambda text, cal=calendar, spinbox=year_spinbox: self._apply_calendar_year_text(
                cal, spinbox, text
            )
        )
        year_spinbox.valueChanged.connect(
            lambda year, cal=calendar: cal.setCurrentPage(year, cal.monthShown())
        )
        year_spinbox._year_stepper_overlay = _YearStepperOverlay(year_spinbox)

    def _apply_calendar_year_text(self, calendar, year_spinbox: QSpinBox, text: str):
        if not text.isdigit() or len(text) < 4:
            return
        year = int(text)
        if year_spinbox.minimum() <= year <= year_spinbox.maximum():
            calendar.setCurrentPage(year, calendar.monthShown())

    def _panel_style(self) -> str:
        return f"""
            QFrame#panelCard {{
                background: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame#panelCard QLabel {{
                background: transparent;
                border: none;
            }}
        """

    def _metric_card_style(self, active: bool) -> str:
        border = COLORS["accent"] if active else COLORS["border"]
        return f"""
            QFrame#panelCard {{
                background: {COLORS['card_bg']};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame#panelCard QLabel {{
                background: transparent;
                border: none;
            }}
        """

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{
                background: {COLORS['card_bg']};
                border: none;
                gridline-color: {COLORS['border_soft']};
                font-size: 13px;
                color: {COLORS['text_dark']};
            }}
            QHeaderView::section {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                font-size: 13px;
                font-weight: 700;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                padding: 6px;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border_soft']};
            }}
            QTableWidget::item:selected {{
                background: #17313A;
                color: {COLORS['text_dark']};
            }}
            QTableWidget::item:focus {{
                border: none;
            }}
            QTableWidget QLineEdit {{
                background: {COLORS['surface']};
                color: {COLORS['text_dark']};
                border: 1px solid {COLORS['accent']};
                border-radius: 4px;
                min-height: 24px;
                padding: 1px 10px;
                selection-background-color: #245C66;
                selection-color: {COLORS['text_dark']};
            }}
            QTableWidget QTableCornerButton::section {{
                background: {COLORS['surface']};
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
