from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PyQt6.QtCore import QDate, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from sqlalchemy import func
from data_simulator import Order, OrderItem, Product, Client, SalesPlan


class AnalyticsWidget(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Фильтры ---
        filter_layout = QHBoxLayout()
        filter_layout.addStretch(2)

        filter_layout.addWidget(QLabel("Период с:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd.MM.yy")
        self.date_from.setStyleSheet("""
            QDateEdit {
                border: 1px solid #26a69a;
                border-radius: 5px;
                padding: 4px 8px;
                background: white;
                color: #004d40;
                font-size: 11pt;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #26a69a;
            }
            QDateEdit::down-arrow {
                image: url(стрелка.png);
                width: 10px;
                height: 10px;
            } 
        """)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("по:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yy")
        self.date_to.setStyleSheet("""
            QDateEdit {
                border: 1px solid #26a69a;
                border-radius: 5px;
                padding: 4px 8px;
                background: white;
                color: #004d40;
                font-size: 11pt;
            }
            QDateEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #26a69a;
            }
            QDateEdit::down-arrow {
                image: url(стрелка.png);
                width: 10px;
                height: 10px;
            } 
        """)
        filter_layout.addWidget(self.date_to)

        self.btn_build = QPushButton("Построить отчёт")
        self.btn_build.setStyleSheet("""
            QPushButton {
                background-color: #26a69a;
                color: white;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e8e7a;
            }
        """)
        self.btn_build.clicked.connect(self.build_report)
        filter_layout.addWidget(self.btn_build)

        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # --- График (сначала) ---
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(5)
        self.table_summary.setHorizontalHeaderLabels(["Дата", "Сумма продаж (₽)", "Прогноз (₽)", "План (₽)", "% выполнения"])
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.table_details = QTableWidget()
        self.table_details.setColumnCount(5)
        self.table_details.setHorizontalHeaderLabels(["Дата", "Продукт", "Клиент", "Количество", "Сумма"])
        self.table_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        splitter.addWidget(self.table_summary)
        splitter.addWidget(self.table_details)
        splitter.setSizes([550, 450])

        main_layout.addWidget(splitter)

    def build_report(self):
        import matplotlib.pyplot as plt  # Импорт для форматирования графика

        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()

        # Запрос продаж по дате, продукту и клиенту, с суммой по строке (цена*количество)
        query = (
            self.session.query(
                Order.order_date,
                Product.name,
                Client.name,
                OrderItem.quantity,
                func.sum(OrderItem.quantity * OrderItem.price).label('line_total')
            )
            .join(OrderItem.order)
            .join(OrderItem.product)
            .join(Order.client)
            .filter(Order.order_date >= date_from)
            .filter(Order.order_date <= date_to)
            .group_by(Order.order_date, Product.name, Client.name)
            .order_by(Order.order_date)
        )

        results = query.all()

        # Запрос планов (без группировки по категориям, сумма по датам)
        plan_query = (
            self.session.query(
                SalesPlan.plan_date,
                func.sum(SalesPlan.forecast_quantity).label('forecast_sum'),
                func.sum(SalesPlan.planned_quantity).label('plan_sum')
            )
            .filter(SalesPlan.plan_date >= date_from)
            .filter(SalesPlan.plan_date <= date_to)
            .group_by(SalesPlan.plan_date)
        )

        plan_results = plan_query.all()
        forecast_by_date = {r.plan_date: r.forecast_sum for r in plan_results}
        plan_by_date = {r.plan_date: r.plan_sum for r in plan_results}

        sales_by_date = {}
        summary_rows = {}
        details_rows = []

        # Обработка результатов продаж
        for order_date, product_name, client_name, quantity, line_total in results:
            # подсчет суммы продаж по дате
            sales_by_date[order_date] = sales_by_date.get(order_date, 0) + line_total
            forecast = forecast_by_date.get(order_date, 0)
            plan = plan_by_date.get(order_date, 0)
            if plan > 0:
                completion = (sales_by_date[order_date] / plan) * 100
            else:
                completion = "-"
            summary_rows[order_date] = [order_date, sales_by_date[order_date], forecast, plan, completion]
            # Для детализации выводим каждую строку заказа с ценой * количеством
            details_rows.append([order_date, product_name, client_name, quantity, line_total])

        # Обработка дат из планов, которых нет в продажах
        for date_key in forecast_by_date:
            if date_key not in summary_rows:
                plan_val = plan_by_date.get(date_key, 0)
                if plan_val > 0:
                    completion = (0 / plan_val) * 100
                else:
                    completion = "-"
                summary_rows[date_key] = [date_key, 0, forecast_by_date[date_key], plan_val, completion]

        # Обновляем таблицу с итогами
        self.table_summary.setRowCount(0)
        self.table_summary.setStyleSheet("""
            QTableWidget {
                gridline-color: #26a69a;
                font-size: 10pt;
                color: #004d40;
                border: none;
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                selection-background-color: #e0f2f1;
                selection-color: #80cbc4;
            }
            QHeaderView::section {
                background-color: #26a69a;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
                border-top-left-radius: 2px;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                margin: 2px 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #b2dfdb;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #26a69a;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                subcontrol-origin: margin;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        for row_data in sorted(summary_rows.values(), key=lambda x: x[0]):
            row = self.table_summary.rowCount()
            self.table_summary.insertRow(row)
            for col, val in enumerate(row_data):
                if col == 0:
                    item = QTableWidgetItem(val.strftime("%d.%m.%y"))
                elif col == 4:
                    item = QTableWidgetItem(f"{val:.2f}%" if isinstance(val, (float, int)) else str(val))
                else:
                    item = QTableWidgetItem(f"{val:.2f}")
                self.table_summary.setItem(row, col, item)

        # Обработка деталей
        self.table_details.setRowCount(0)
        self.table_details.setStyleSheet("""
            QTableWidget {
                gridline-color: #26a69a;
                font-size: 10pt;
                color: #004d40;
                border: none;
                background-color: #ffffff;
                alternate-background-color: #f9f9f9;
                selection-background-color: #e0f2f1;
                selection-color: #80cbc4;
            }
            QHeaderView::section {
                background-color: #26a69a;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
                border-top-left-radius: 2px;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                margin: 2px 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #b2dfdb;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #26a69a;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                subcontrol-origin: margin;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        for row_data in details_rows:
            row = self.table_details.rowCount()
            self.table_details.insertRow(row)
            for col, val in enumerate(row_data):
                if col == 0:
                    item = QTableWidgetItem(val.strftime("%d.%m.%y"))
                elif col == 4:
                    item = QTableWidgetItem(f"{val:.2f}")
                else:
                    item = QTableWidgetItem(str(val))
                self.table_details.setItem(row, col, item)

        # Построение графика
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        dates = sorted(set(list(sales_by_date.keys()) + list(forecast_by_date.keys())))
        date_labels = [d.strftime("%d.%m.%y") for d in dates]
        totals = [sales_by_date.get(d, 0) for d in dates]
        forecast_values = [forecast_by_date.get(d, 0) for d in dates]
        plan_values = [plan_by_date.get(d, 0) for d in dates]

        # Форматирование оси Y
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))

        ax.bar(date_labels, totals, color="#80cbc4", edgecolor="#004d40", linewidth=1.2, alpha=0.9, label="Продажи (₽)")
        ax.plot(date_labels, forecast_values, color="#004d40", linestyle="--", linewidth=2, marker='s', markersize=3,
                label="Прогноз спроса (₽)")
        ax.plot(date_labels, plan_values, color="#26a69a", linestyle="-.", linewidth=2, marker='^', markersize=3,
                label="План продаж (₽)")

        ax.set_title("Сумма продаж, прогноз и план", fontsize=11, color="#004d40", fontweight='bold')
        ax.tick_params(axis='x', rotation=45, labelsize=7, colors="#004d40")
        ax.tick_params(axis='y', labelsize=7, colors="#004d40")
        ax.legend(facecolor='white', edgecolor='lightgray', fontsize=8)
        ax.grid(True, linestyle='--', alpha=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor("#26a69a")

        self.figure.tight_layout()
        self.canvas.draw()