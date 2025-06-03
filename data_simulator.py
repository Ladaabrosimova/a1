import random
import threading
import time
from datetime import date, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

Base = declarative_base()

# Модели таблиц
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    price = Column(Float)
    shelf_life = Column(Integer)
    temperature_sensitive = Column(Boolean)
    brand = Column(String)
    stock_quantity = Column(Integer)
    ph_level = Column(Float, nullable=True)

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    client_type = Column(String)
    region = Column(String)
    orders = relationship("Order", backref="client")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    order_date = Column(Date)
    status = Column(String)
    items = relationship("OrderItem", backref="order")

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    price = Column(Float)
    product = relationship("Product")

class MarketingActivity(Base):
    __tablename__ = 'marketing_activities'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(String)
    products = relationship("ActivityProduct", back_populates="activity")

class ActivityProduct(Base):
    __tablename__ = 'activity_products'
    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('marketing_activities.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    activity = relationship("MarketingActivity", back_populates="products")
    product = relationship("Product")

class SalesPlan(Base):
    __tablename__ = 'sales_plan'
    id = Column(Integer, primary_key=True)
    plan_date = Column(Date)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    planned_quantity = Column(Float)
    forecast_quantity = Column(Float)
    product = relationship("Product")

# Инициализация базы данных
engine = create_engine('sqlite:///pm_demo.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class DataSimulator:
    def __init__(self, interval_seconds=0.5):
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self.iteration = 0
        self.categories = ["Крем", "Сыворотка", "Филлер"]

    def start(self):
        """Запускает симулятор в отдельном потоке."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            logger.info("Симулятор запущен")

    def stop(self):
        """Останавливает симулятор."""
        self.running = False
        if self.thread:
            self.thread.join()
            logger.info("Симулятор остановлен")

    def run(self):
        """Основной цикл симуляции."""
        while self.running:
            session = Session()
            try:
                self.generate_new_order(session)
                self.adjust_inventory(session)
                if self.iteration % 5 == 0:
                    self.generate_marketing_activity(session)
                self.iteration += 1
            except Exception as e:
                logger.error(f"Ошибка симуляции: {e}")
                session.rollback()
            finally:
                session.close()
            time.sleep(self.interval)

    def populate_initial_data(self, session):
        """Заполняет начальные данные для всех таблиц."""
        logger.info("Начало заполнения начальных данных")
        session.query(ActivityProduct).delete()
        session.query(MarketingActivity).delete()
        session.query(OrderItem).delete()
        session.query(Order).delete()
        session.query(Client).delete()
        session.query(Product).delete()
        session.query(SalesPlan).delete()
        session.commit()

        # Заполнение таблицы products
        for i in range(100):
            category = random.choice(self.categories)
            product = Product(
                name=f"Продукт {i+1}",
                category=category,
                price=round(random.uniform(1000, 10000), 2),
                shelf_life=random.randint(30, 365),
                temperature_sensitive=random.choice([True, False]),
                brand=f"Бренд {random.randint(1, 10)}",
                stock_quantity=random.randint(10, 100),
                ph_level=round(random.uniform(4.5, 7.5), 1) if category in ["Крем", "Сыворотка"] else None
            )
            session.add(product)
        session.commit()
        logger.info("Таблица products заполнена")

        # Заполнение таблицы clients
        regions = ["Москва", "Санкт-Петербург", "Регионы"]
        for i in range(50):
            session.add(Client(
                name=f"Клиент {i+1}",
                client_type=random.choice(["косметолог", "клиника"]),
                region=random.choice(regions)
            ))
        session.commit()
        logger.info("Таблица clients заполнена")

        # Заполнение таблиц orders и order_items (10 заказов на день)
        clients = session.query(Client).all()
        products = session.query(Product).all()
        start_date = date.today() - timedelta(days=365)
        end_date = date.today() - timedelta(days=1)
        orders_per_day = 10

        for day_offset in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=day_offset)
            for _ in range(orders_per_day):
                order = Order(
                    client=random.choice(clients),
                    order_date=current_date,
                    status="Выполнен"
                )
                session.add(order)
                session.flush()

                for _ in range(random.randint(1, 5)):
                    product = random.choice(products)
                    quantity = random.randint(1, 10)
                    price = round(product.price * quantity, 2)
                    session.add(OrderItem(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=price
                    ))
                session.commit()
            logger.debug(f"Создано {orders_per_day} заказов для {current_date}")

        logger.info(f"Таблицы orders и order_items заполнены: ~{orders_per_day * 365} заказов")

        # Заполнение таблиц marketing_activities и activity_products
        for i in range(10):
            start_date = date.today() - timedelta(days=random.randint(10, 30))
            end_date = start_date + timedelta(days=random.randint(5, 15))
            activity = MarketingActivity(
                name=f"Акция {i+1000}",
                start_date=start_date,
                end_date=end_date,
                description=f"Скидки на товары {i+1}"
            )
            session.add(activity)
            session.commit()

            for product in random.sample(products, min(5, len(products))):
                session.add(ActivityProduct(activity=activity, product=product))
            session.commit()
        logger.info("Таблицы marketing_activities и activity_products заполнены")

    def generate_new_order(self, session):
        """Генерирует заказы для сегодняшней даты, чтобы их было столько же, как и раньше."""
        clients = session.query(Client).all()
        products = session.query(Product).all()
        if not clients or not products:
            logger.warning("Нет клиентов или продуктов для создания заказа")
            return

        current_date = date.today()

        # Проверяем, сколько заказов уже есть на сегодня
        existing_orders_count = session.query(Order).filter(Order.order_date == current_date).count()

        # Определяем желаемое число заказов на день
        desired_orders_per_day = 10

        # Создаем недостающие заказы
        for _ in range(desired_orders_per_day - existing_orders_count):
            order = Order(
                client=random.choice(clients),
                order_date=current_date,
                status="Выполнен"
            )
            session.add(order)
            session.flush()

            for _ in range(random.randint(1, 5)):
                product = random.choice(products)
                quantity = random.randint(1, 10)
                price = round(product.price * quantity, 2)
                session.add(OrderItem(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price
                ))
            session.commit()
            logger.debug(f"Создан заказ №{order.id} от {current_date}")

    def adjust_inventory(self, session):
        """Корректирует запасы продуктов."""
        for product in session.query(Product).all():
            change = random.randint(-3, 3)
            product.stock_quantity = max(0, (product.stock_quantity or 0) + change)
        session.commit()
        logger.debug("Запасы продуктов скорректированы")

    def generate_marketing_activity(self, session):
        """Генерирует новую маркетинговую активность."""
        products = session.query(Product).all()
        if not products:
            logger.warning("Нет продуктов для маркетинговой активности")
            return
        name = f"Акция {random.randint(1000, 9999)}"
        start_date = date.today() - timedelta(days=random.randint(0, 10))
        end_date = start_date + timedelta(days=random.randint(5, 15))
        activity = MarketingActivity(
            name=name,
            start_date=start_date,
            end_date=end_date,
            description="Скидки на товары"
        )
        session.add(activity)
        session.commit()

        for product in random.sample(products, min(5, len(products))):
            session.add(ActivityProduct(activity=activity, product=product))
        session.commit()
        logger.debug(f"Добавлена маркетинговая активность: {activity.name}")


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    simulator = DataSimulator(interval_seconds=2)
    session = Session()
    simulator.populate_initial_data(session)
    session.close()
    simulator.start()
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        simulator.stop()