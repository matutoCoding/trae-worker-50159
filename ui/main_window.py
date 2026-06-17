from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QListWidget,
                             QListWidgetItem, QStackedWidget, QLabel, QVBoxLayout,
                             QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

from .dashboard_page import DashboardPage
from .pet_page import PetPage
from .workstation_page import WorkstationPage
from .service_page import ServicePage
from .appointment_page import AppointmentPage
from .schedule_page import SchedulePage
from .billing_page import BillingPage
from .member_page import MemberPage
from .inventory_page import InventoryPage
from .settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('萌宠之家 - 美容预约管理系统')
        self.resize(1360, 860)
        self.setMinimumSize(1200, 760)
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        logo_label = QLabel('🐾 萌宠之家')
        logo_label.setObjectName('logoLabel')
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedHeight(80)
        sidebar_layout.addWidget(logo_label)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName('navList')
        self.nav_list.setIconSize(QSize(20, 20))
        self.nav_list.setSpacing(2)

        nav_items = [
            ('📊  数据概览', DashboardPage),
            ('🐕  宠物档案', PetPage),
            ('�  会员管理', MemberPage),
            ('📦  库存管理', InventoryPage),
            ('�🛁  工位管理', WorkstationPage),
            ('✂️  服务项目', ServicePage),
            ('📅  美容预约', AppointmentPage),
            ('🗓  排期看板', SchedulePage),
            ('💳  账单管理', BillingPage),
            ('⚙️  系统设置', SettingsPage),
        ]
        for text, page_cls in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, page_cls)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            item.setSizeHint(QSize(0, 52))
            self.nav_list.addItem(item)

        sidebar_layout.addWidget(self.nav_list, 1)

        footer = QLabel('v1.0.0  ©2026')
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName('footerLabel')
        footer.setFixedHeight(40)
        sidebar_layout.addWidget(footer)

        self.pages = QStackedWidget()
        self.pages.setObjectName('pages')

        self._page_cache = {}
        for i in range(self.nav_list.count()):
            placeholder = QWidget()
            self.pages.addWidget(placeholder)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)

        content_frame = QFrame()
        content_frame.setObjectName('contentFrame')
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.pages)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_frame, 1)

    def _on_nav_changed(self, row):
        item = self.nav_list.item(row)
        if not item:
            return
        page_cls = item.data(Qt.ItemDataRole.UserRole)
        if row not in self._page_cache:
            page = page_cls()
            old = self.pages.widget(row)
            self.pages.removeWidget(old)
            self.pages.insertWidget(row, page)
            self._page_cache[row] = page
        self.pages.setCurrentIndex(row)
        if hasattr(self._page_cache[row], 'refresh'):
            self._page_cache[row].refresh()

    def _apply_style(self):
        self.setStyleSheet('''
            QMainWindow { background: #f0f2f5; }
            #sidebar {
                background: #1f2937;
                border-right: 1px solid #111827;
            }
            #logoLabel {
                color: #fbbf24;
                font-size: 22px;
                font-weight: bold;
                background: #111827;
                border-bottom: 1px solid #0f172a;
                letter-spacing: 2px;
            }
            #footerLabel {
                color: #6b7280;
                font-size: 11px;
                background: #111827;
                border-top: 1px solid #0f172a;
            }
            #navList {
                background: transparent;
                border: none;
                outline: 0;
                padding: 12px 0;
            }
            #navList::item {
                color: #d1d5db;
                font-size: 15px;
                padding: 0 24px;
                border-left: 3px solid transparent;
            }
            #navList::item:hover {
                background: #374151;
                color: #fff;
            }
            #navList::item:selected {
                background: #374151;
                color: #fbbf24;
                border-left: 3px solid #fbbf24;
                font-weight: bold;
            }
            #contentFrame {
                background: #f0f2f5;
            }
            #pages {
                background: #f0f2f5;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #c7cbd1;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background: #9ca3af; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        ''')
