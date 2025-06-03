from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
import numpy as np
from sqlalchemy import func
from datetime import date, timedelta, datetime
import pandas as pd
import logging
from prophet import Prophet
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from data_simulator import Product, Order, OrderItem, SalesPlan, MarketingActivity, Client, ActivityProduct

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ForecastWidget(QWidget):
    """Виджет для прогнозирования спроса и планирования продаж по продуктам в денежных единицах с графиком Matplotlib."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.init_ui()
        self.build_forecast_and_plan()

    def init_ui(self):
        """Инициализирует пользовательский интерфейс виджета."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        filter_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить прогноз и план")
        self.btn_save.setContentsMargins(10, 30, 30, 10)
        self.btn_save.setFixedHeight(30)
        self.btn_save.setStyleSheet("""
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
        self.btn_save.clicked.connect(self.save_forecast_and_plan)
        filter_layout.addStretch(2)
        filter_layout.addWidget(self.btn_save)
        main_layout.addLayout(filter_layout)

        self.figure, self.ax = plt.subplots(figsize=(10, 4))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("border: 1px solid #26a69a; border-radius: 5px;")
        main_layout.addWidget(self.canvas)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Дата", "Продукт", "Прогноз спроса (₽)", "План продаж (₽)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(180)
        self.table.setStyleSheet("""
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
        main_layout.addWidget(self.table)

    def get_client_activity(self, session, date_from, date_to):
        """Анализ активности клиентов из CRM."""
        try:
            query = (
                session.query(
                    Client.id,
                    func.count(Order.id).label("order_count"),
                    func.avg(OrderItem.quantity * OrderItem.price).label("avg_check")
                )
                .join(Order, Client.id == Order.client_id)
                .join(OrderItem, Order.id == OrderItem.order_id)
                .filter(Order.order_date >= date_from)
                .filter(Order.order_date <= date_to)
                .group_by(Client.id)
            )
            results = query.all()
            client_activity = {r.id: {"order_count": r.order_count, "avg_check": r.avg_check or 0} for r in results}
            logger.debug(f"Найдено активностей клиентов: {len(client_activity)}")
            return client_activity
        except Exception as e:
            logger.error(f"Ошибка получения активности клиентов: {str(e)}")
            return {}

    def build_forecast_and_plan(self):
        """Строит прогноз спроса и план продаж по продуктам с использованием Prophet."""
        try:
            logger.debug("Начало построения прогноза и плана по продуктам")
            forecast_days = 30
            today = date.today()
            forecast_dates = [today + timedelta(days=i) for i in range(forecast_days)]
            date_to = today - timedelta(days=1)
            date_from = date_to - timedelta(days=365)

            # Получение данных о товарах
            products = self.session.query(Product).all()
            logger.debug(f"Найдено продуктов: {len(products)}")
            if not products:
                logger.warning("Нет данных о продуктах")
                QMessageBox.warning(self, "Ошибка", "Нет данных о продуктах в базе.")
                self.table.setRowCount(0)
                self.ax.clear()
                self.canvas.draw()
                return

            product_info = {}
            for p in products:
                # Преобразование shelf_life из строки в datetime.date, если необходимо
                shelf_life = p.shelf_life
                if isinstance(shelf_life, str):
                    try:
                        shelf_life = datetime.strptime(shelf_life, "%Y-%m-%d").date()
                        logger.debug(f"Преобразовано shelf_life для продукта ID={p.id}: {shelf_life}")
                    except ValueError:
                        logger.warning(f"Некорректный формат shelf_life для продукта ID={p.id}: {shelf_life}")
                        shelf_life = None
                product_info[p.id] = {
                    "name": p.name,
                    "shelf_life": shelf_life,
                    "ph_level": p.ph_level
                }

            prices = {p.id: p.price for p in products}

            # Исторические данные о продажах по продуктам
            query = (
                self.session.query(
                    Order.order_date,
                    Product.id,
                    func.sum(OrderItem.quantity * OrderItem.price).label("total_revenue")
                )
                .join(OrderItem, Order.id == OrderItem.order_id)
                .join(Product, OrderItem.product_id == Product.id)
                .filter(Order.order_date >= date_from)
                .filter(Order.order_date <= date_to)
                .group_by(Order.order_date, Product.id)
            )
            results = query.all()
            logger.debug(f"Найдено записей продаж: {len(results)}")
            for r in results[:5]:
                logger.debug(f"Продажи: Дата={r.order_date}, Продукт ID={r.id}, Выручка={r.total_revenue}")

            if not results:
                logger.warning("Нет данных о продажах")
                QMessageBox.warning(self, "Ошибка", "Нет данных о продажах за указанный период.")
                self.table.setRowCount(0)
                self.ax.clear()
                self.canvas.draw()
                return

            # Подготовка данных для Prophet
            sales_by_date = {}
            for r in results:
                date_key = r.order_date
                product_id = r.id
                if date_key not in sales_by_date:
                    sales_by_date[date_key] = {}
                sales_by_date[date_key][product_id] = sales_by_date[date_key].get(product_id, 0) + (r.total_revenue or 0)

            # Заполнение пропущенных дат
            for d in pd.date_range(date_from, date_to):
                if d.date() not in sales_by_date:
                    sales_by_date[d.date()] = {pid: 0 for pid in product_info.keys()}

            # Прогноз для каждого продукта
            forecasts = {}
            for product_id in product_info.keys():
                df = []
                for d in pd.date_range(date_from, date_to):
                    revenue = sales_by_date.get(d.date(), {}).get(product_id, 0)
                    df.append({"ds": pd.Timestamp(d), "y": revenue})
                df = pd.DataFrame(df)
                logger.debug(f"Данные для продукта ID={product_id} ({product_info[product_id]['name']}): {len(df)} записей, сумма={df['y'].sum()}")

                if df["y"].sum() <= 0:
                    logger.debug(f"Пропуск продукта ID={product_id}: нулевая выручка")
                    continue

                model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                    seasonality_mode="multiplicative"
                )
                model.fit(df)
                future = model.make_future_dataframe(periods=forecast_days)
                forecast = model.predict(future)
                forecasts[product_id] = forecast.tail(forecast_days)[["ds", "yhat"]]

            if not forecasts:
                logger.warning("Нет данных для прогноза")
                QMessageBox.warning(self, "Ошибка", "Нет ненулевой выручки для продуктов.")
                self.table.setRowCount(0)
                self.ax.clear()
                self.canvas.draw()
                return

            # Учет активности клиентов
            client_activity = self.get_client_activity(self.session, date_from, date_to)
            avg_order_count = np.mean([v["order_count"] for v in client_activity.values()]) if client_activity else 1
            client_adj = {cid: 1 + 0.05 * (act["order_count"] - avg_order_count) / (avg_order_count or 1)
                          for cid, act in client_activity.items()}

            # Учет маркетинговых активностей
            activities = self.session.query(MarketingActivity).filter(
                MarketingActivity.start_date <= max(forecast_dates),
                MarketingActivity.end_date >= min(forecast_dates)
            ).all()
            logger.debug(f"Найдено маркетинговых активностей: {len(activities)}")

            # Формирование прогноза и плана
            self.forecast_data = []
            product_forecasts = {pid: [] for pid in forecasts.keys()}
            product_plans = {pid: [] for pid in forecasts.keys()}
            for i, f_date in enumerate(forecast_dates):
                for product_id, forecast in forecasts.items():
                    f_row = forecast[forecast["ds"] == pd.Timestamp(f_date)]
                    if not f_row.empty:
                        base_forecast = f_row["yhat"].iloc[0]
                        monthly_adj = 1.1 if f_date.month in [3, 4, 5, 9, 10, 11] else 1.0
                        marketing_adj = 1.1 if any(
                            a.start_date <= f_date <= a.end_date and any(
                                ap.product_id == product_id for ap in a.products
                            ) for a in activities
                        ) else 1.0
                        shelf_life = product_info[product_id]["shelf_life"]
                        logger.debug(f"Продукт ID={product_id}, shelf_life={shelf_life}, тип={type(shelf_life)}, f_date={f_date}")
                        shelf_life_adj = 0.5 if shelf_life and isinstance(shelf_life, date) and shelf_life <= f_date else 1.0
                        ph_level = product_info[product_id]["ph_level"]
                        ph_adj = 1.2 if ph_level and 5.0 <= ph_level <= 6.0 else 1.0
                        client_activity_adj = np.mean(list(client_adj.values())) if client_adj else 1.0
                        product_forecast = max(
                            base_forecast * monthly_adj * marketing_adj * shelf_life_adj * ph_adj * client_activity_adj,
                            0)
                        product_forecasts[product_id].append(product_forecast)
                        plan_factor = 1.05
                        if any(a.start_date <= f_date <= a.end_date for a in activities):
                            plan_factor += 0.05
                        product_plans[product_id].append(max(product_forecast * plan_factor, 0))
                        self.forecast_data.append({
                            'date': f_date,
                            'product_id': product_id,
                            'product_name': product_info[product_id]["name"],
                            'forecast': product_forecast,
                            'plan': product_forecast * plan_factor
                        })

            # Агрегация для отображения
            total_forecasts = []
            total_plans = []
            for i, f_date in enumerate(forecast_dates):
                total_forecast = sum(product_forecasts[pid][i] for pid in product_forecasts)
                total_plan = sum(product_plans[pid][i] for pid in product_plans)
                total_forecasts.append(total_forecast)
                total_plans.append(total_plan)

            # Заполнение таблицы
            self.table.setRowCount(0)
            for data in self.forecast_data:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(data['date'].strftime("%d.%m.%Y")))
                self.table.setItem(row, 1, QTableWidgetItem(data['product_name']))
                self.table.setItem(row, 2, QTableWidgetItem(f"{data['forecast']:.2f} ₽"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{data['plan']:.2f} ₽"))

            # Построение графика (агрегированные данные по всем продуктам)
            self.ax.clear()
            date_labels = [d.strftime("%d.%m.%Y") for d in forecast_dates]
            self.ax.plot(
                date_labels, total_forecasts,
                label="Прогноз спроса (₽)",
                color="#26a69a",
                linestyle="--",
                marker='s',
                linewidth=2,
                markersize=3,
            )
            self.ax.plot(
                date_labels, total_plans,
                label="План продаж (₽)",
                color="#80cbc4",
                linestyle="-.",
                marker='^',
                linewidth=2,
                markersize=3,
            )
            for i, f_date in enumerate(forecast_dates):
                if any(a.start_date <= f_date <= a.end_date for a in activities):
                    self.ax.axvline(x=date_labels[i], color='red', linestyle=':', alpha=0.3, linewidth=1)
            self.ax.set_title(f"Прогноз и план на 30 дней (все продукты)", color="#004d40", fontsize=14, fontweight="bold")
            self.ax.legend(facecolor='white', edgecolor='lightgray', fontsize=8)
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.tick_params(axis='x', rotation=45, colors="#004d40", labelsize=7)
            self.ax.tick_params(axis='y', colors="#004d40", labelsize=7)
            for spine in self.ax.spines.values():
                spine.set_edgecolor("#b0b0b0")
                spine.set_linewidth = 0.8
            self.ax.set_facecolor('white')
            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            logger.error(f"Ошибка при построении прогноза и плана: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось построить прогноз и план: {str(e)}")
            self.table.setRowCount(0)
            self.ax.clear()
            self.canvas.draw()

    def save_forecast_and_plan(self):
        """Сохраняет прогноз и план в базу данных с двумя знаками после запятой."""
        try:
            logger.debug(f"Попытка сохранить {len(self.forecast_data)} записей прогноза")
            if not self.forecast_data:
                logger.warning("Нет данных для сохранения в forecast_data")
                QMessageBox.warning(self, "Предупреждение", "Нет данных прогноза для сохранения.")
                return

            saved_count = 0
            updated_count = 0

            for data in self.forecast_data:
                logger.debug(
                    f"Обработка записи: Дата={data['date']}, Продукт={data['product_name']}, Прогноз={data['forecast']}, План={data['plan']}"
                )
                plan_date = data['date']
                product_id = data['product_id']

                # Проверка наличия существующего плана
                existing_plan = self.session.query(SalesPlan).filter_by(
                    plan_date=plan_date,
                    product_id=product_id
                ).first()

                if existing_plan:
                    # Обновление существующего плана
                    existing_plan.planned_quantity = round(data['plan'], 2)
                    existing_plan.forecast_quantity = round(data['forecast'], 2)
                    self.session.add(existing_plan)
                    updated_count += 1
                    logger.debug(f"Обновлен план: Дата={plan_date}, Продукт ID={product_id}")
                else:
                    # Создание нового плана
                    plan = SalesPlan(
                        plan_date=plan_date,
                        product_id=product_id,
                        planned_quantity=round(data['plan'], 2),
                        forecast_quantity=round(data['forecast'], 2)
                    )
                    self.session.add(plan)
                    saved_count += 1
                    logger.debug(f"Создан новый план: Дата={plan_date}, Продукт ID={product_id}")

            self.session.commit()
            logger.info(f"Сохранено {saved_count} новых записей, обновлено {updated_count} существующих записей")
            QMessageBox.information(
                self, "Успех",
                f"Сохранено {saved_count} новых записей и обновлено {updated_count} записей в базе данных."
            )

        except Exception as e:
            logger.error(f"Ошибка при сохранении прогноза и плана: {str(e)}")
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить прогноз и план: {str(e)}")