from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QSpinBox, QMessageBox, QFrame, QTabWidget)
from PyQt6.QtCore import Qt
from models import Member, MemberTransaction


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:8px 20px;
             border-radius:6px; font-weight:bold; border:none; }
             QPushButton:hover { background:#f59e0b; }'''

def _btn_secondary():
    return '''QPushButton { background:#e5e7eb; color:#374151; padding:8px 20px;
             border-radius:6px; border:none; } QPushButton:hover { background:#d1d5db; }'''

def _btn_danger():
    return '''QPushButton { background:#fee2e2; color:#b91c1c; padding:6px 14px;
             border-radius:5px; border:none; } QPushButton:hover { background:#fecaca; }'''

def _btn_success():
    return '''QPushButton { background:#10b981; color:#fff; padding:6px 14px;
             border-radius:5px; border:none; font-weight:bold; }
             QPushButton:hover { background:#059669; }'''

def _line_edit_style():
    return '''QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
             padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
             background:#fff; font-size:13px; }
             QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }'''


class MemberFormDialog(QDialog):
    def __init__(self, parent=None, member=None):
        super().__init__(parent)
        self.member = member
        self.setWindowTitle('新建会员' if not member else '编辑会员')
        self.resize(440, 360)
        self._build()

    def _build(self):
        lay = QFormLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        self.ed_owner = QLineEdit()
        self.ed_owner.setPlaceholderText('宠主姓名')
        lay.addRow('宠主姓名*:', self.ed_owner)

        self.ed_phone = QLineEdit()
        self.ed_phone.setPlaceholderText('手机号')
        lay.addRow('联系电话*:', self.ed_phone)

        self.cb_level = QComboBox()
        self.cb_level.addItems(['普通卡', '银卡', '金卡', '钻石卡'])
        lay.addRow('会员等级:', self.cb_level)

        self.sp_balance = QDoubleSpinBox()
        self.sp_balance.setRange(0, 99999)
        self.sp_balance.setDecimals(2)
        self.sp_balance.setPrefix('¥ ')
        lay.addRow('初始余额:', self.sp_balance)

        self.sp_points = QSpinBox()
        self.sp_points.setRange(0, 999999)
        lay.addRow('初始积分:', self.sp_points)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton('💾 保存')
        btn_save.setStyleSheet(_btn_primary())
        btn_save.clicked.connect(self._save)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        lay.addRow(btn_row)

        if self.member:
            self.ed_owner.setText(self.member.owner_name or '')
            self.ed_phone.setText(self.member.owner_phone or '')
            idx = self.cb_level.findText(self.member.level or '普通卡')
            if idx >= 0:
                self.cb_level.setCurrentIndex(idx)
            self.sp_balance.setValue(self.member.balance or 0)
            self.sp_points.setValue(self.member.points or 0)

    def _save(self):
        name = self.ed_owner.text().strip()
        phone = self.ed_phone.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, '提示', '请填写宠主姓名和联系电话')
            return
        self.result_data = {
            'owner_name': name,
            'owner_phone': phone,
            'level': self.cb_level.currentText(),
            'balance': self.sp_balance.value(),
            'points': self.sp_points.value()
        }
        self.accept()


class RechargeDialog(QDialog):
    def __init__(self, parent=None, member=None):
        super().__init__(parent)
        self.member = member
        self.setWindowTitle(f'充值 - {member.owner_name}')
        self.resize(360, 260)
        self._build()

    def _build(self):
        lay = QFormLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)
        info = QLabel(f'等级: {self.member.level} | 当前余额: ¥{self.member.balance:.2f} | 积分: {self.member.points}')
        info.setStyleSheet('color:#2563eb; font-weight:bold; padding:6px 0;')
        lay.addRow(info)

        self.sp_amount = QDoubleSpinBox()
        self.sp_amount.setRange(1, 99999)
        self.sp_amount.setDecimals(2)
        self.sp_amount.setSingleStep(50)
        self.sp_amount.setPrefix('¥ ')
        self.sp_amount.setValue(100)
        lay.addRow('充值金额*:', self.sp_amount)

        self.ed_note = QLineEdit()
        self.ed_note.setPlaceholderText('如: 充500送50活动')
        lay.addRow('备注:', self.ed_note)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('确认充值')
        btn_ok.setStyleSheet(_btn_primary())
        btn_ok.clicked.connect(self._ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addRow(btn_row)

    def _ok(self):
        if self.sp_amount.value() <= 0:
            QMessageBox.warning(self, '提示', '充值金额必须大于0')
            return
        self.result_data = {'amount': self.sp_amount.value(), 'note': self.ed_note.text().strip()}
        self.accept()


class MemberPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        header_row = QHBoxLayout()
        title = QLabel('👥 会员管理')
        title.setStyleSheet('font-size:24px; font-weight:bold; color:#111827; padding:8px 0;')
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet('color:#2563eb; font-weight:bold; font-size:14px;')
        header_row.addWidget(self.lbl_total)
        root.addLayout(header_row)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 搜索姓名/电话...')
        self.ed_search.setStyleSheet(_line_edit_style() + 'QLineEdit { padding:9px 14px; }')
        self.ed_search.returnPressed.connect(self.refresh)
        toolbar.addWidget(self.ed_search, 1)
        btn_search = QPushButton('搜索')
        btn_search.setStyleSheet(_btn_secondary())
        btn_search.clicked.connect(self.refresh)
        toolbar.addWidget(btn_search)
        btn_add = QPushButton('➕ 新建会员')
        btn_add.setStyleSheet(_btn_primary())
        btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(btn_add)
        root.addLayout(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('''
            QTabWidget::pane { border:1px solid #e5e7eb; border-radius:8px; background:#fff; }
            QTabBar::tab { padding:10px 24px; font-weight:bold; color:#6b7280; }
            QTabBar::tab:selected { color:#111827; border-bottom:2px solid #fbbf24; }
        ''')

        self.tbl_member = QTableWidget(0, 7)
        self.tbl_member.setHorizontalHeaderLabels(['ID', '宠主', '电话', '等级', '余额', '积分', '操作'])
        self.tbl_member.verticalHeader().setVisible(False)
        self.tbl_member.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_member.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_member.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_member.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; font-size:13px; }
            QHeaderView::section { background:#f9fafb; padding:12px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
            QTableWidget::item { padding:10px; }
        ''')
        self.tabs.addTab(self.tbl_member, '📋 会员列表')

        trans_tab = QWidget()
        trans_lay = QVBoxLayout(trans_tab)
        trans_lay.setContentsMargins(16, 16, 16, 16)
        tbar = QHBoxLayout()
        tbar.addWidget(QLabel('选择会员:'))
        self.cb_member = QComboBox()
        self.cb_member.currentIndexChanged.connect(self._refresh_trans)
        tbar.addWidget(self.cb_member)
        tbar.addStretch(1)
        trans_lay.addLayout(tbar)
        self.tbl_trans = QTableWidget(0, 5)
        self.tbl_trans.setHorizontalHeaderLabels(['时间', '类型', '金额(¥)', '积分变动', '备注'])
        self.tbl_trans.verticalHeader().setVisible(False)
        self.tbl_trans.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_trans.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_trans.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_trans.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; font-size:13px; }
            QHeaderView::section { background:#f9fafb; padding:12px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
        ''')
        trans_lay.addWidget(self.tbl_trans, 1)
        self.tabs.addTab(trans_tab, '📝 流水记录')

        root.addWidget(self.tabs, 1)

    def refresh(self):
        kw = self.ed_search.text().strip() or None
        members = Member.list(kw)
        self.tbl_member.setRowCount(0)
        total_balance = 0
        self.cb_member.clear()
        self.cb_member.addItem('全部会员', None)
        for m in members:
            total_balance += m.balance or 0
            r = self.tbl_member.rowCount()
            self.tbl_member.insertRow(r)
            items = [str(m.id), m.owner_name, m.owner_phone, m.level,
                     f'¥{m.balance:.2f}', str(m.points)]
            for col, val in enumerate(items):
                it = QTableWidgetItem(val)
                if col == 3:
                    if m.level == '钻石卡':
                        it.setForeground(Qt.GlobalColor.darkYellow)
                    elif m.level == '金卡':
                        it.setForeground(Qt.GlobalColor.darkGreen)
                    elif m.level == '银卡':
                        it.setForeground(Qt.GlobalColor.darkCyan)
                    it.setText(f'⭐ {val}')
                if col == 4:
                    it.setForeground(Qt.GlobalColor.darkBlue)
                self.tbl_member.setItem(r, col, it)
            op = QWidget()
            op_lay = QHBoxLayout(op)
            op_lay.setContentsMargins(4, 2, 4, 2)
            op_lay.setSpacing(4)
            btn_r = QPushButton('充值')
            btn_r.setStyleSheet(_btn_success())
            btn_r.clicked.connect(lambda _, _m=m: self._on_recharge(_m))
            btn_e = QPushButton('编辑')
            btn_e.setStyleSheet(_btn_secondary())
            btn_e.clicked.connect(lambda _, _m=m: self._on_edit(_m))
            btn_d = QPushButton('删除')
            btn_d.setStyleSheet(_btn_danger())
            btn_d.clicked.connect(lambda _, _m=m: self._on_delete(_m))
            op_lay.addStretch(1)
            op_lay.addWidget(btn_r)
            op_lay.addWidget(btn_e)
            op_lay.addWidget(btn_d)
            self.tbl_member.setCellWidget(r, 6, op)
            self.tbl_member.setRowHeight(r, 42)
            self.cb_member.addItem(f'{m.owner_name} ({m.owner_phone}) {m.level}', m.id)
        self.lbl_total.setText(f'会员 {len(members)} 名 | 储值余额合计 ¥{total_balance:.2f}')

    def _refresh_trans(self):
        mid = self.cb_member.currentData()
        if mid:
            trans = MemberTransaction.list_by_member(mid)
        else:
            trans = []
            if self.cb_member.count() > 1:
                first_id = self.cb_member.itemData(1)
                if first_id:
                    trans = MemberTransaction.list_by_member(first_id)
        self.tbl_trans.setRowCount(0)
        for t in trans:
            r = self.tbl_trans.rowCount()
            self.tbl_trans.insertRow(r)
            type_map = {'recharge': '💰 充值', 'consume': '💸 消费', 'adjust': '📝 调整', 'award': '🎁 赠送'}
            self.tbl_trans.setItem(r, 0, QTableWidgetItem((t.created_at or '').split('.')[0]))
            self.tbl_trans.setItem(r, 1, QTableWidgetItem(type_map.get(t.type_, t.type_)))
            amt = QTableWidgetItem(f'{t.amount:+.2f}')
            if t.amount > 0:
                amt.setForeground(Qt.GlobalColor.darkGreen)
            elif t.amount < 0:
                amt.setForeground(Qt.GlobalColor.red)
            self.tbl_trans.setItem(r, 2, amt)
            pt = QTableWidgetItem(f'{t.points_delta:+d}' if t.points_delta else '0')
            if t.points_delta and t.points_delta > 0:
                pt.setForeground(Qt.GlobalColor.darkBlue)
            self.tbl_trans.setItem(r, 3, pt)
            self.tbl_trans.setItem(r, 4, QTableWidgetItem(t.note or ''))

    def _on_add(self):
        dlg = MemberFormDialog(self)
        if dlg.exec():
            Member.add(dlg.result_data)
            self.refresh()

    def _on_edit(self, member):
        dlg = MemberFormDialog(self, member)
        if dlg.exec():
            Member.update(member.id, dlg.result_data)
            self.refresh()

    def _on_recharge(self, member):
        dlg = RechargeDialog(self, member)
        if dlg.exec():
            m, err = Member.recharge(member.id, dlg.result_data['amount'], dlg.result_data['note'])
            if err:
                QMessageBox.warning(self, '充值失败', err)
            else:
                QMessageBox.information(self, '充值成功',
                                        f'会员 {m.owner_name} 充值成功\n当前余额: ¥{m.balance:.2f}')
            self.refresh()

    def _on_delete(self, member):
        r = QMessageBox.question(self, '确认删除',
                                 f'确定删除会员 {member.owner_name} ({member.owner_phone})？\n该会员关联的流水记录将被删除。',
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            Member.delete(member.id)
            self.refresh()
