from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QDialog,
    QCalendarWidget, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import QDate, Qt, QSize
from datetime import datetime, timedelta

class DatePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите дату")
        self.resize(300, 250)
        layout = QVBoxLayout(self)

        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_date(self):
        return self.calendar.selectedDate()

class OverviewWidget(QWidget):
    def __init__(self, analytics_widget, parent=None):
        super().__init__(parent)
        self.analytics_widget = analytics_widget

        self.current_mode = "week"
        self.current_date = datetime.today().date()

        self.init_ui()
        self.load_data_for_current_mode()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # Кнопки обзора (день/неделя/месяц) - ВЕРТИКАЛЬНО
        buttons_vlayout = QVBoxLayout()
        buttons_vlayout.setSpacing(8)

        self.btn_week = QPushButton("Недельный обзор")
        self.btn_month = QPushButton("Месячный обзор")
        self.btn_day = QPushButton("Дневной обзор")
        for btn in (self.btn_week, self.btn_month, self.btn_day):
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setFixedWidth(230)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px;
                    padding: 4px;
                    border-radius: 6px;
                }
                QPushButton:checked {
                    background-color: #26a69a;
                    color: white;
                }
            """)
            buttons_vlayout.addWidget(btn)

        self.btn_week.setChecked(True)
        self.btn_week.clicked.connect(self.on_week_clicked)
        self.btn_month.clicked.connect(self.on_month_clicked)
        self.btn_day.clicked.connect(self.on_day_clicked)

        layout.addLayout(buttons_vlayout)

        # Кнопки навигации ← →
        self.btn_prev = QPushButton("<<")
        self.btn_next = QPushButton(">>")
        for btn in (self.btn_prev, self.btn_next):
            btn.setFixedSize(QSize(70, 70))
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 20px;
                    padding: 4px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #26a69a;
                    color: white;
                }
            """)
        self.btn_prev.clicked.connect(self.on_prev_clicked)
        self.btn_next.clicked.connect(self.on_next_clicked)

        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addStretch()

    def load_data_for_current_mode(self):
        if self.current_mode == "week":
            start, end = self.get_week_range(self.current_date)
        elif self.current_mode == "month":
            start, end = self.get_month_range(self.current_date)
        else:
            start = end = self.current_date

        self.analytics_widget.date_from.setDate(QDate(start.year, start.month, start.day))
        self.analytics_widget.date_to.setDate(QDate(end.year, end.month, end.day))
        self.analytics_widget.build_report()

    def on_week_clicked(self):
        self.current_mode = "week"
        self.btn_week.setChecked(True)
        self.btn_month.setChecked(False)
        self.btn_day.setChecked(False)
        self.load_data_for_current_mode()

    def on_month_clicked(self):
        self.current_mode = "month"
        self.btn_week.setChecked(False)
        self.btn_month.setChecked(True)
        self.btn_day.setChecked(False)
        self.load_data_for_current_mode()

    def on_day_clicked(self):
        self.current_mode = "day"
        self.btn_week.setChecked(False)
        self.btn_month.setChecked(False)
        self.btn_day.setChecked(True)
        self.open_date_picker()

    def open_date_picker(self):
        dlg = DatePickerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            qdate = dlg.selected_date()
            self.current_date = qdate.toPyDate()
        else:
            self.current_mode = "week"
            self.btn_week.setChecked(True)
            self.btn_day.setChecked(False)
            self.btn_month.setChecked(False)
        self.load_data_for_current_mode()

    def on_prev_clicked(self):
        if self.current_mode == "week":
            self.current_date -= timedelta(days=7)
        elif self.current_mode == "month":
            year = self.current_date.year
            month = self.current_date.month - 1
            if month < 1:
                month = 12
                year -= 1
            self.current_date = self.current_date.replace(year=year, month=month, day=1)
        else:
            self.current_date -= timedelta(days=1)
        self.load_data_for_current_mode()

    def on_next_clicked(self):
        if self.current_mode == "week":
            self.current_date += timedelta(days=7)
        elif self.current_mode == "month":
            year = self.current_date.year
            month = self.current_date.month + 1
            if month > 12:
                month = 1
                year += 1
            self.current_date = self.current_date.replace(year=year, month=month, day=1)
        else:
            self.current_date += timedelta(days=1)
        self.load_data_for_current_mode()

    @staticmethod
    def get_week_range(date):
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return start, end

    @staticmethod
    def get_month_range(date):
        start = date.replace(day=1)
        next_month = start.month + 1
        year = start.year
        if next_month == 13:
            next_month = 1
            year += 1
        next_month_start = start.replace(year=year, month=next_month, day=1)
        end = next_month_start - timedelta(days=1)
        return start, end
