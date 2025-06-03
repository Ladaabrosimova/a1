import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from interface import Ui_MainWindow
from analytics_w import AnalyticsWidget
from forecast_w import ForecastWidget
from stok_w import StokWidget
from main_tab import OverviewWidget
from data_simulator import Session


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.session = Session()

        # Центральные виджеты
        self.analytics_widget = AnalyticsWidget(self.session)
        self.prognoz_widget = ForecastWidget(self.session)
        self.inventory_widget = StokWidget(self.session)

        self.overview_widget = OverviewWidget(self.analytics_widget)

        self.ui.topTabStack.addWidget(self.overview_widget)

        # Основные центральные вкладки
        self.ui.stackedWidget.addWidget(self.analytics_widget)
        self.ui.stackedWidget.addWidget(self.prognoz_widget)
        self.ui.stackedWidget.addWidget(self.inventory_widget)

        self.ui.listWidget.currentRowChanged.connect(self.ui.stackedWidget.setCurrentIndex)
        self.ui.topTabList.currentRowChanged.connect(self.ui.topTabStack.setCurrentIndex)

        self.ui.listWidget.setCurrentRow(0)
        self.ui.topTabList.setCurrentRow(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
