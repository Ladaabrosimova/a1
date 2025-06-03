from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
from datetime import datetime
from data_simulator import Product


class StokWidget(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #cccccc;
                border-radius: 10px;
                background-color: #f8f9fa;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                margin: 4px 0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #e0f2f1;
                border-radius: 6px;
                min-height: 15px;
            }
            QScrollBar::handle:vertical:hover {
                background: #26a69a;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)

        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        self.load_products()

    def load_products(self):
        products = self.session.query(Product).all()
        today = datetime.today().date()
        products.sort(key=lambda p: p.shelf_life)

        for product in products:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet(self.get_style_for_product(product, today))
            hbox = QHBoxLayout(frame)

            name_label = QLabel(f"<b>{product.name}</b> ({product.brand})")
            name_label.setFixedWidth(150)
            hbox.addWidget(name_label)

            info = f"""
                Тип: {product.category} |
                Цена: {product.price} ₽ |
                Остаток: {product.stock_quantity} |
                Срок годности: {product.shelf_life} дн.
            """
            info_label = QLabel(info)
            hbox.addWidget(info_label)

            self.scroll_layout.addWidget(frame)

        self.scroll_layout.addStretch()

    def get_style_for_product(self, product, today):
        if product.shelf_life < 60:
            return """
                QFrame {
                    background-color: #ffe0e0;
                    border: 2px solid #d32f2f;
                    border-radius: 8px;
                    padding: 8px;
                }
            """
        return """
            QFrame {
                background-color: #e0f2f1;
                border: 1px solid #26a69a;
                border-radius: 8px;
                padding: 8px;
            }
        """
