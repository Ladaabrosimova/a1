from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget
)


class IconListWidget(QtWidgets.QListWidget):
    def __init__(self, icon_paths, icon_hover_paths, parent=None):
        super().__init__(parent)
        self.icon_paths = icon_paths
        self.icon_hover_paths = icon_hover_paths
        self.setMouseTracking(True)
        self.current_hover_row = -1

        self.itemEntered.connect(self.on_item_entered)
        self.currentRowChanged.connect(self.on_current_row_changed)

    def addItemWithIcon(self, text):
        item = QListWidgetItem(text)
        if text in self.icon_paths:
            item.setIcon(QIcon(self.icon_paths[text]))
        self.addItem(item)

    def on_item_entered(self, item):
        row = self.row(item)
        if row != self.current_hover_row:
            self.reset_icon_if_not_selected(self.current_hover_row)
            self.current_hover_row = row
            if not item.isSelected() and item.text() in self.icon_hover_paths:
                item.setIcon(QIcon(self.icon_hover_paths[item.text()]))

    def on_current_row_changed(self, current_row):
        for i in range(self.count()):
            item = self.item(i)
            if i == current_row:
                if item.text() in self.icon_hover_paths:
                    item.setIcon(QIcon(self.icon_hover_paths[item.text()]))
            else:
                self.reset_icon_if_not_selected(i)

    def reset_icon_if_not_selected(self, row):
        if row < 0 or row >= self.count():
            return
        item = self.item(row)
        if not item.isSelected() and item.text() in self.icon_paths:
            item.setIcon(QIcon(self.icon_paths[item.text()]))

    def leaveEvent(self, event):
        for i in range(self.count()):
            item = self.item(i)
            if item.isSelected() and item.text() in self.icon_hover_paths:
                item.setIcon(QIcon(self.icon_hover_paths[item.text()]))
            elif item.text() in self.icon_paths:
                item.setIcon(QIcon(self.icon_paths[item.text()]))
        self.current_hover_row = -1
        super().leaveEvent(event)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(933, 599)
        MainWindow.setWindowState(QtCore.Qt.WindowState.WindowMaximized)

        self.centralwidget = QWidget()
        MainWindow.setCentralWidget(self.centralwidget)

        self.main_vlayout = QVBoxLayout(self.centralwidget)
        self.main_vlayout.setSpacing(1)
        self.main_vlayout.setContentsMargins(5, 5, 5, 5)

        # --- Верхние вкладки ---
        self.topTabList = QtWidgets.QListWidget()
        self.topTabList.setObjectName("topTabList")
        self.topTabList.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.topTabList.setFixedHeight(40)
        self.topTabList.setSpacing(0)
        self.topTabList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_vlayout.addWidget(self.topTabList, 1)

        self.topTabStack = QStackedWidget()
        self.topTabStack.setObjectName("topTabStack")
        self.topTabStack.setFixedHeight(90)
        self.main_vlayout.addWidget(self.topTabStack, 2)

        # Добавим названия вкладок без содержимого
        for tab_name in ["Главная", " "]:
            self.topTabList.addItem(tab_name)

        self.topTabStack.setStyleSheet("background-color: #e0f2f1;")

        # --- Основная горизонтальная область ---
        self.content_hlayout = QHBoxLayout()
        self.content_hlayout.setSpacing(1)
        self.main_vlayout.addLayout(self.content_hlayout)

        # Левая панель
        icon_paths = {
            "Аналитика продаж": "1.png",
            "Прогнозирование спроса": "2.png",
            "Управление запасами": "3.png",
        }
        icon_hover_paths = {
            "Аналитика продаж": "1_2.png",
            "Прогнозирование спроса": "2_2.png",
            "Управление запасами": "3_2.png",
        }
        self.listWidget = IconListWidget(icon_paths, icon_hover_paths, parent=self.centralwidget)
        self.listWidget.setIconSize(QtCore.QSize(32, 32))
        self.listWidget.setFixedWidth(230)
        self.content_hlayout.addWidget(self.listWidget, 1)

        # Правая панель (пока пустая)
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.content_hlayout.addWidget(self.stackedWidget, 3)

        self.retranslateUi(MainWindow)
        self.set_styles(MainWindow)

    def set_styles(self, MainWindow):
        style = """
        QWidget {
            background-color: #ffffff;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            font-size: 11pt;
            color: #004d40;
        }
        
        QListWidget#topTabList {
            background-color: #ffffff;
            padding: 0px;
            margin: 5px;
            border: none;
            margin-bottom: -6px;
        }
        
        QListWidget#topTabList::item {
            background-color: #26a69a;
            border: 2px solid #26a69a;
            color: white;
            border-bottom: none;
            border-radius: 6px;
            margin: 1px;
            padding: 8px 16px;
        }
        
        QListWidget#topTabList::item:selected {
            background-color: #e0f2f1;
            color: #004d40;
            border: 2px solid #26a69a;
            border-bottom: none;
        }
        
        QListWidget#topTabList::item:hover {
            background-color: #e0f2f1;
            color: #004d40;
            border: 2px solid #26a69a;
            border-bottom: none;
        }

        QListWidget {
            background-color: #e0f2f1;
            border: 2px solid #26a69a;
            border-radius: 6px;
            padding: 5px;
            color: #004d40;
        }
        
        QListWidget::item {
            padding: 8px 10px;
            margin: 2px;
            border-radius: 4px;
        }
        
        QListWidget::item:selected {
            background-color: #26a69a;
            color: white;
        }
        
        QListWidget::item:hover {
            background-color: #4db6ac;
            color: white;
        }
        
        QStackedWidget {
            background-color: #ffffff;
            border: 2px solid #26a69a;
            border-radius: 6px;
        }
        
        QStackedWidget#topTabStack {
            background-color: #e0f2f1;
            border: 2px solid #26a69a;
            border-bottom-left-radius: 6px;
            border-bottom-right-radius: 6px;
        }


        """
        MainWindow.setStyleSheet(style)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Аптечка Косметолога"))
        self.listWidget.clear()
        for text in [
            "Аналитика продаж",
            "Прогнозирование спроса",
            "Управление запасами",
        ]:
            self.listWidget.addItemWithIcon(text)



