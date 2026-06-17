from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QGridLayout, QDateEdit, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from modules import BillingEngine
from models import Appointment


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(22)

        header = QLabel('📊 数据概览')
        header.setObjectName('pageTitle')
        header.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(header)

        filters = QHBoxLayout()
        filters.setSpacing(12)
        filters.addWidget(QLabel('统计区间:'))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        self.date_from.setStyleSheet(self._date_style())
        filters.addWidget(self.date_from)
        filters.addWidget(QLabel('至'))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        self.date_to.setStyleSheet(self._date_style())
        filters.addWidget(self.date_to)
        btn_refresh = QPushButton('🔄 刷新统计')
        btn_refresh.clicked.connect(self.refresh)
        btn_refresh.setStyleSheet(self._btn_primary())
        filters.addWidget(btn_refresh)
        filters.addStretch(1)
        root.addLayout(filters)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(16)
        root.addLayout(self.stats_grid)

        self.info_label = QLabel('系统就绪 · 宠物美容预约管理平台')
        self.info_label.setStyleSheet('color:#6b7280; font-size:13px; padding-top:8px;')
        root.addWidget(self.info_label)

        root.addStretch(1)

    def _date_style(self):
        return '''
            QDateEdit {
                padding: 6px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background: #fff;
                font-size: 13px;
            }
            QDateEdit:focus { border: 1px solid #fbbf24; }
        '''

    def _btn_primary(self):
        return '''
            QPushButton {
                background: #fbbf24;
                color: #1f2937;
                padding: 7px 18px;
                border-radius: 6px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background: #f59e0b; }
        '''

    def _stat_card(self, title, value, sub_text, color):
        card = QFrame()
        card.setObjectName('statCard')
        card.setStyleSheet(f'''
            #statCard {{
                background: #fff;
                border-radius: 12px;
                border-top: 4px solid {color};
            }}
        ''')
        card.setMinimumHeight(140)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet('color:#6b7280; font-size:13px;')
        v = QLabel(str(value))
        v.setStyleSheet(f'color:{color}; font-size:32px; font-weight:bold;')
        s = QLabel(sub_text)
        s.setStyleSheet('color:#9ca3af; font-size:12px;')
        layout.addWidget(t)
        layout.addWidget(v)
        layout.addWidget(s)
        layout.addStretch(1)
        return card

    def refresh(self):
        try:
            for i in reversed(range(self.stats_grid.count())):
                w = self.stats_grid.itemAt(i).widget()
                if w:
                    w.setParent(None)

            df = self.date_from.date().toString('yyyy-MM-dd')
            dt = self.date_to.date().toString('yyyy-MM-dd')
            stats = BillingEngine.get_dashboard_stats(df, dt)

            bill_count = stats.get('bill_count', 0) or 0
            total = stats.get('total_amount', 0) or 0
            paid = stats.get('paid_total', 0) or 0
            unpaid = stats.get('unpaid_total', 0) or 0
            cap_count = stats.get('cap_count', 0) or 0
            pet_count = stats.get('pet_count', 0) or 0
            ws_count = stats.get('workstation_count', 0) or 0
            today_count = len(Appointment.list_by_date(QDate.currentDate().toString('yyyy-MM-dd')))
            member_total_balance = stats.get('member_total_balance', 0) or 0
            member_count = stats.get('member_count', 0) or 0
            low_stock_count = stats.get('low_stock_count', 0) or 0
            inv_consumed_7d = stats.get('inv_consumed_7d', 0) or 0
            inv_consumed_value_7d = stats.get('inv_consumed_value_7d', 0) or 0

            low_stock_items = stats.get('low_stock_items', []) or []
            low_sub = '需尽快补货'
            if low_stock_items:
                first = low_stock_items[0]
                low_sub = f'{first.get("name", "?")}: 剩{first.get("stock", 0)}/{first.get("min_stock", 0)}'
                if len(low_stock_items) > 1:
                    low_sub += f' 等{low_stock_count}项'

            cards = [
                ('营业总额', f'¥{total:,.2f}', f'{df} ~ {dt}', '#10b981'),
                ('已收款', f'¥{paid:,.2f}', '已结清订单', '#3b82f6'),
                ('待收款', f'¥{unpaid:,.2f}', '未结清订单', '#ef4444'),
                ('开单数', f'{bill_count} 单', f'封顶单 {cap_count} 单', '#8b5cf6'),
                ('👥 会员储值', f'¥{member_total_balance:,.2f}', f'会员 {member_count} 名', '#2563eb'),
                ('🧴 近7天耗材', f'{inv_consumed_7d} 件', f'消耗 ¥{inv_consumed_value_7d:,.2f}', '#0891b2'),
                ('⚠️ 低库存项目', f'{low_stock_count} 项', low_sub, '#dc2626'),
                ('今日预约', f'{today_count} 条', '排期订单', '#f59e0b'),
                ('在档宠物', f'{pet_count} 只', '已建立档案', '#06b6d4'),
                ('可用工位', f'{ws_count} 个', '当前工位总数', '#ec4899'),
            ]
            for i, (t, v, s, c) in enumerate(cards):
                r, col = divmod(i, 5)
                self.stats_grid.addWidget(self._stat_card(t, v, s, c), r, col)

            low_parts = []
            if low_stock_items:
                for it in low_stock_items[:5]:
                    name = it.get('name', '?')
                    stock = it.get('stock', 0)
                    min_stock = it.get('min_stock', 0)
                    low_parts.append(f'{name}(剩{stock}/安全{min_stock})')
            low_text = ''
            if low_parts:
                low_text = ' | ⚠️ 低库存: ' + '，'.join(low_parts)

            self.info_label.setText(
                f'统计区间: {df} 至 {dt}  |  营业 ¥{total:,.2f}  |  预约 {today_count} 单  |  在档宠物 {pet_count} 只'
                f'  |  会员储值 ¥{member_total_balance:,.2f}  |  近7天耗材 ¥{inv_consumed_value_7d:,.2f}{low_text}'
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.info_label.setText(f'⚠️ 统计加载出现异常: {e}')
