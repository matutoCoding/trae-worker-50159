from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QSpinBox, QTextEdit, QMessageBox, QFrame, QSizePolicy,
                             QTabWidget, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from models import Inventory, InventoryTransaction, ServiceInventoryLink, Service


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:8px 20px;
             border-radius:6px; font-weight:bold; }
             QPushButton:hover { background:#f59e0b; }'''

def _btn_danger():
    return '''QPushButton { background:#ef4444; color:#fff; padding:8px 16px;
             border-radius:6px; } QPushButton:hover { background:#dc2626; }'''

def _btn_secondary():
    return '''QPushButton { background:#6b7280; color:#fff; padding:8px 16px;
             border-radius:6px; } QPushButton:hover { background:#4b5563; }'''

def _section_title():
    return '''QLabel { font-size:20px; font-weight:bold; color:#111827; padding:8px 0; }'''


class InventoryFormDialog(QDialog):
    def __init__(self, parent=None, inv=None):
        super().__init__(parent)
        self.inv = inv
        self.result = {}
        self.setWindowTitle('耗材档案' if inv else '新增耗材')
        self.resize(420, 460)
        self._build()

    def _build(self):
        lay = QFormLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        self.ed_name = QLineEdit(self.inv.name if self.inv else '')
        self.ed_name.setPlaceholderText('如: 宠物沐浴露')
        lay.addRow('耗材名称*:', self.ed_name)

        self.cb_cat = QComboBox()
        for c in ['洗护耗材', 'SPA耗材', '医疗耗材', '工具耗材', '清洁耗材', '防护耗材', '其他']:
            self.cb_cat.addItem(c)
        if self.inv and self.inv.category:
            idx = self.cb_cat.findText(self.inv.category)
            if idx >= 0:
                self.cb_cat.setCurrentIndex(idx)
        lay.addRow('分类:', self.cb_cat)

        self.ed_unit = QLineEdit(self.inv.unit if self.inv else '份')
        lay.addRow('计量单位:', self.ed_unit)

        self.sp_stock = QSpinBox()
        self.sp_stock.setRange(0, 99999)
        self.sp_stock.setValue(self.inv.stock if self.inv else 0)
        if self.inv:
            self.sp_stock.setEnabled(False)
            lay.addRow('当前库存:', self.sp_stock)
            hint = QLabel('⚠️ 编辑模式下不可直接改库存，请用"入库"或"盘点"功能')
            hint.setStyleSheet('color:#f59e0b; font-size:11px; padding:2px 0;')
            lay.addRow('', hint)
        else:
            lay.addRow('初始库存:', self.sp_stock)

        self.sp_min = QSpinBox()
        self.sp_min.setRange(0, 99999)
        self.sp_min.setValue(self.inv.min_stock if self.inv else 0)
        lay.addRow('低库存阈值:', self.sp_min)

        self.sp_price = QDoubleSpinBox()
        self.sp_price.setRange(0, 99999)
        self.sp_price.setDecimals(2)
        self.sp_price.setSingleStep(1)
        self.sp_price.setValue(self.inv.unit_price if self.inv else 0)
        lay.addRow('单价(¥):', self.sp_price)

        self.ed_notes = QTextEdit(self.inv.notes if self.inv else '')
        self.ed_notes.setPlaceholderText('备注信息...')
        self.ed_notes.setFixedHeight(80)
        lay.addRow('备注:', self.ed_notes)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('保存')
        btn_ok.setStyleSheet(_btn_primary())
        btn_ok.clicked.connect(self._ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addRow(btn_row)

    def _ok(self):
        if not self.ed_name.text().strip():
            QMessageBox.warning(self, '提示', '请填写耗材名称')
            return
        self.result = {
            'name': self.ed_name.text().strip(),
            'category': self.cb_cat.currentText(),
            'unit': self.ed_unit.text().strip() or '份',
            'stock': self.sp_stock.value(),
            'min_stock': self.sp_min.value(),
            'unit_price': self.sp_price.value(),
            'notes': self.ed_notes.toPlainText().strip()
        }
        self.accept()


class StockInDialog(QDialog):
    def __init__(self, parent=None, inv=None):
        super().__init__(parent)
        self.inv = inv
        self.result = {}
        self.setWindowTitle(f'入库 - {inv.name}' if inv else '入库')
        self.resize(380, 260)
        self._build()

    def _build(self):
        lay = QFormLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)
        info = QLabel(f'当前库存: {self.inv.stock} {self.inv.unit}') if self.inv else QLabel('')
        info.setStyleSheet('color:#374151; font-weight:bold;')
        lay.addRow(info)

        self.sp_qty = QSpinBox()
        self.sp_qty.setRange(1, 99999)
        self.sp_qty.setValue(10)
        lay.addRow('入库数量*:', self.sp_qty)

        self.sp_price = QDoubleSpinBox()
        self.sp_price.setRange(0, 99999)
        self.sp_price.setDecimals(2)
        self.sp_price.setSingleStep(1)
        self.sp_price.setValue(self.inv.unit_price if self.inv else 0)
        lay.addRow('入库单价(¥):', self.sp_price)

        self.ed_note = QLineEdit()
        self.ed_note.setPlaceholderText('如: 采购自XX供应商')
        lay.addRow('备注:', self.ed_note)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('确认入库')
        btn_ok.setStyleSheet(_btn_primary())
        btn_ok.clicked.connect(self._ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addRow(btn_row)

    def _ok(self):
        if self.sp_qty.value() <= 0:
            QMessageBox.warning(self, '提示', '入库数量必须大于0')
            return
        self.result = {
            'quantity': self.sp_qty.value(),
            'unit_price': self.sp_price.value(),
            'note': self.ed_note.text().strip()
        }
        self.accept()


class StockAdjustDialog(QDialog):
    def __init__(self, parent=None, inv=None):
        super().__init__(parent)
        self.inv = inv
        self.result = {}
        self.setWindowTitle(f'库存盘点 - {inv.name}' if inv else '库存盘点')
        self.resize(380, 280)
        self._build()

    def _build(self):
        lay = QFormLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        info = QLabel(f'当前系统库存: {self.inv.stock} {self.inv.unit}' if self.inv else '')
        info.setStyleSheet('color:#374151; font-weight:bold;')
        lay.addRow(info)

        self.sp_actual = QSpinBox()
        self.sp_actual.setRange(0, 99999)
        self.sp_actual.setValue(self.inv.stock if self.inv else 0)
        self.sp_actual.valueChanged.connect(self._update_diff)
        lay.addRow('实际盘点数量*:', self.sp_actual)

        self.lbl_diff = QLabel('')
        self.lbl_diff.setStyleSheet('color:#6b7280; font-size:12px; padding:4px 0;')
        lay.addRow('差异:', self.lbl_diff)

        self.cb_reason = QComboBox()
        for r in ['正常损耗', '盘盈', '盘亏', '过期报损', '其他原因']:
            self.cb_reason.addItem(r)
        lay.addRow('原因:', self.cb_reason)

        self.ed_note = QLineEdit()
        self.ed_note.setPlaceholderText('可补充说明盘点详情')
        lay.addRow('备注:', self.ed_note)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('确认盘点')
        btn_ok.setStyleSheet(_btn_primary())
        btn_ok.clicked.connect(self._ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addRow(btn_row)

        self._update_diff()

    def _update_diff(self):
        if not self.inv:
            return
        diff = self.sp_actual.value() - self.inv.stock
        if diff > 0:
            self.lbl_diff.setText(f'<span style="color:#10b981;">盘盈 +{diff} {self.inv.unit}</span>')
        elif diff < 0:
            self.lbl_diff.setText(f'<span style="color:#ef4444;">盘亏 {diff} {self.inv.unit}</span>')
        else:
            self.lbl_diff.setText('<span style="color:#6b7280;">账实相符，无差异</span>')

    def _ok(self):
        if self.sp_actual.value() < 0:
            QMessageBox.warning(self, '提示', '库存数量不能为负')
            return
        diff = self.sp_actual.value() - (self.inv.stock if self.inv else 0)
        reason = self.cb_reason.currentText()
        note = self.ed_note.text().strip()
        full_note = f'[{reason}] {note}' if note else f'[{reason}] 盘点调整'
        self.result = {
            'actual_stock': self.sp_actual.value(),
            'diff': diff,
            'reason': reason,
            'note': full_note
        }
        self.accept()


class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel('📦 库存管理')
        title.setStyleSheet(_section_title())
        header.addWidget(title)
        header.addStretch(1)
        self.lbl_stat = QLabel('')
        self.lbl_stat.setStyleSheet('color:#6b7280; font-size:13px; padding:4px 12px;')
        header.addWidget(self.lbl_stat)
        self.btn_add = QPushButton('+ 新增耗材')
        self.btn_add.setStyleSheet(_btn_primary())
        self.btn_add.clicked.connect(self._on_add)
        header.addWidget(self.btn_add)
        root.addLayout(header)

        search_bar = QFrame()
        search_bar.setStyleSheet('QFrame{background:#fff; border-radius:8px; padding:10px;}')
        sb_lay = QHBoxLayout(search_bar)
        sb_lay.setContentsMargins(12, 8, 12, 8)
        sb_lay.setSpacing(10)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('搜索耗材名称/分类...')
        self.ed_search.setStyleSheet('QLineEdit{padding:8px 12px; border:1px solid #e5e7eb; border-radius:6px;}')
        self.ed_search.textChanged.connect(lambda _: self.refresh())
        sb_lay.addWidget(self.ed_search, 1)
        self.chk_low = QPushButton('🔴 只看低库存')
        self.chk_low.setCheckable(True)
        self.chk_low.setStyleSheet('''
            QPushButton{padding:8px 14px; border-radius:6px; border:1px solid #e5e7eb; background:#fff;}
            QPushButton:checked{background:#fef2f2; color:#dc2626; border-color:#fca5a5; font-weight:bold;}
        ''')
        self.chk_low.clicked.connect(self.refresh)
        sb_lay.addWidget(self.chk_low)
        root.addWidget(search_bar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('''
            QTabWidget::pane { border:1px solid #e5e7eb; border-radius:8px; background:#fff; }
            QTabBar::tab { padding:10px 24px; border-radius:6px; }
            QTabBar::tab:selected { background:#fbbf24; color:#1f2937; font-weight:bold; }
            QTabBar::tab:!selected { background:#fff; color:#6b7280; }
        ''')
        root.addWidget(self.tabs, 1)

        inv_page = QWidget()
        inv_lay = QVBoxLayout(inv_page)
        inv_lay.setContentsMargins(12, 12, 12, 12)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['ID', '耗材名称', '分类', '单位', '库存', '阈值', '单价', '操作'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; }
            QHeaderView::section { background:#f9fafb; padding:10px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
            QTableWidget::item { padding:8px; }
        ''')
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        inv_lay.addWidget(self.table)
        self.tabs.addTab(inv_page, '耗材库存')

        tx_page = QWidget()
        tx_lay = QVBoxLayout(tx_page)
        tx_lay.setContentsMargins(12, 12, 12, 12)
        tx_list_row = QHBoxLayout()
        tx_list_row.addWidget(QLabel('选择耗材查看流水:'))
        self.lb_inv = QListWidget()
        self.lb_inv.setFixedWidth(180)
        self.lb_inv.itemClicked.connect(self._refresh_tx)
        self.tx_table = QTableWidget(0, 6)
        self.tx_table.setHorizontalHeaderLabels(['时间', '类型', '数量', '结存', '单价', '备注'])
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tx_table.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; }
            QHeaderView::section { background:#f9fafb; padding:10px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
            QTableWidget::item { padding:8px; }
        ''')
        self.tx_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        tx_list_row.addWidget(self.lb_inv)
        tx_list_row.addWidget(self.tx_table, 1)
        tx_lay.addLayout(tx_list_row)
        self.tabs.addTab(tx_page, '出入库流水')

        svc_page = QWidget()
        svc_lay = QVBoxLayout(svc_page)
        svc_lay.setContentsMargins(12, 12, 12, 12)
        hint = QLabel('为每个服务项目关联需要消耗的耗材，开单时自动扣减库存。')
        hint.setStyleSheet('color:#6b7280; padding:8px 0;')
        svc_lay.addWidget(hint)
        self.svc_table = QTableWidget(0, 3)
        self.svc_table.setHorizontalHeaderLabels(['服务项目', '关联耗材', '操作'])
        self.svc_table.verticalHeader().setVisible(False)
        self.svc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.svc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.svc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.svc_table.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; }
            QHeaderView::section { background:#f9fafb; padding:10px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
            QTableWidget::item { padding:8px; }
        ''')
        svc_lay.addWidget(self.svc_table)
        self.tabs.addTab(svc_page, '服务耗材关联')

    def refresh(self):
        kw = self.ed_search.text().strip() if hasattr(self, 'ed_search') else ''
        only_low = self.chk_low.isChecked() if hasattr(self, 'chk_low') else False
        items = Inventory.list(keyword=kw or None, only_low=only_low)
        self.table.setRowCount(0)
        low_count = 0
        total_value = 0
        for inv in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            if inv.stock <= inv.min_stock:
                low_count += 1
            total_value += inv.stock * inv.unit_price
            vals = [str(inv.id), inv.name, inv.category or '-', inv.unit,
                    str(inv.stock), str(inv.min_stock), f'¥{inv.unit_price:.2f}']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if inv.stock <= inv.min_stock and c == 4:
                    it.setForeground(Qt.GlobalColor.red)
                    it.setText(f'{inv.stock} ⚠')
                self.table.setItem(r, c, it)
            op_w = QWidget()
            op_lay = QHBoxLayout(op_w)
            op_lay.setContentsMargins(0, 0, 0, 0)
            op_lay.setSpacing(4)
            btn_in = QPushButton('入库')
            btn_in.setStyleSheet(_btn_primary())
            btn_in.setFixedWidth(50)
            btn_in.clicked.connect(lambda _, i=inv: self._on_stock_in(i))
            btn_adj = QPushButton('盘点')
            btn_adj.setStyleSheet('''QPushButton{background:#0ea5e9; color:#fff; padding:6px 10px; border-radius:5px; border:none;}
                                     QPushButton:hover{background:#0284c7;}''')
            btn_adj.setFixedWidth(50)
            btn_adj.clicked.connect(lambda _, i=inv: self._on_stock_adjust(i))
            btn_edit = QPushButton('编辑')
            btn_edit.setStyleSheet(_btn_secondary())
            btn_edit.setFixedWidth(50)
            btn_edit.clicked.connect(lambda _, i=inv: self._on_edit(i))
            btn_del = QPushButton('删除')
            btn_del.setStyleSheet(_btn_danger())
            btn_del.setFixedWidth(50)
            btn_del.clicked.connect(lambda _, i=inv: self._on_del(i))
            op_lay.addStretch(1)
            op_lay.addWidget(btn_in)
            op_lay.addWidget(btn_adj)
            op_lay.addWidget(btn_edit)
            op_lay.addWidget(btn_del)
            self.table.setCellWidget(r, 7, op_w)

        self.lbl_stat.setText(f'共 {len(items)} 项耗材 | 低库存 {low_count} 项 | 库存总值 ¥{total_value:.2f}')

        self.lb_inv.clear()
        for inv in Inventory.list():
            it = QListWidgetItem(f'{inv.name} ({inv.stock}{inv.unit})')
            it.setData(Qt.ItemDataRole.UserRole, inv.id)
            self.lb_inv.addItem(it)
        if self.lb_inv.count() > 0:
            self.lb_inv.setCurrentRow(0)
            self._refresh_tx()

        services = Service.list()
        self.svc_table.setRowCount(0)
        for s in services:
            r = self.svc_table.rowCount()
            self.svc_table.insertRow(r)
            self.svc_table.setItem(r, 0, QTableWidgetItem(f'{s.name} ({s.category})'))
            links = ServiceInventoryLink.list_by_service(s.id)
            link_str = '、'.join(f"{l.get('inv_name','?')}×{l.get('quantity',1)}" for l in links) or '—'
            self.svc_table.setItem(r, 1, QTableWidgetItem(link_str))
            btn_edit = QPushButton('设置关联')
            btn_edit.setStyleSheet(_btn_primary())
            btn_edit.clicked.connect(lambda _, sv=s: self._on_edit_links(sv))
            self.svc_table.setCellWidget(r, 2, btn_edit)

    def _refresh_tx(self, item=None):
        if item is None:
            item = self.lb_inv.currentItem()
        if not item:
            return
        inv_id = item.data(Qt.ItemDataRole.UserRole)
        txs = InventoryTransaction.list_by_inventory(inv_id, limit=200)
        type_map = {
            'stock_in': '📥 入库',
            'stock_out': '📤 出库',
            'service_use': '🛁 服务消耗',
            'adjust_in': '📊 盘盈',
            'adjust_out': '📊 盘亏',
        }
        self.tx_table.setRowCount(0)
        for tx in txs:
            r = self.tx_table.rowCount()
            self.tx_table.insertRow(r)
            qty = tx.quantity
            qty_str = f'+{qty}' if qty > 0 else str(qty)
            qty_item = QTableWidgetItem(qty_str)
            if qty > 0:
                qty_item.setForeground(Qt.GlobalColor.darkGreen)
            elif qty < 0:
                qty_item.setForeground(Qt.GlobalColor.red)
            time_str = (tx.created_at or '').split('.')[0]
            self.tx_table.setItem(r, 0, QTableWidgetItem(time_str))
            self.tx_table.setItem(r, 1, QTableWidgetItem(type_map.get(tx.type_, tx.type_)))
            self.tx_table.setItem(r, 2, qty_item)
            self.tx_table.setItem(r, 3, QTableWidgetItem(f'{tx.stock_after}'))
            self.tx_table.setItem(r, 4, QTableWidgetItem(f'¥{tx.unit_price:.2f}'))
            self.tx_table.setItem(r, 5, QTableWidgetItem(tx.note or ''))

    def _on_add(self):
        d = InventoryFormDialog(self)
        if d.exec():
            Inventory.add(d.result)
            self.refresh()

    def _on_edit(self, inv):
        d = InventoryFormDialog(self, inv)
        if d.exec():
            Inventory.update(inv.id, d.result)
            self.refresh()

    def _on_stock_in(self, inv):
        d = StockInDialog(self, inv)
        if d.exec():
            _, err = Inventory.stock_in(inv.id, d.result['quantity'],
                                         d.result.get('unit_price'), d.result.get('note'))
            if err:
                QMessageBox.warning(self, '入库失败', err)
            self.refresh()

    def _on_stock_adjust(self, inv):
        d = StockAdjustDialog(self, inv)
        if d.exec():
            res = d.result
            new_inv, err = Inventory.stock_adjust(inv.id, res['actual_stock'], res['note'])
            if err:
                QMessageBox.warning(self, '盘点失败', err)
            else:
                diff = res['diff']
                if diff > 0:
                    msg = f'盘盈 +{diff} {inv.unit}\n盘点后库存: {new_inv.stock} {inv.unit}'
                elif diff < 0:
                    msg = f'盘亏 {diff} {inv.unit}\n盘点后库存: {new_inv.stock} {inv.unit}'
                else:
                    msg = f'账实相符，无变化\n库存: {new_inv.stock} {inv.unit}'
                QMessageBox.information(self, '盘点完成', msg)
            self.refresh()

    def _on_del(self, inv):
        links = ServiceInventoryLink.list_by_inventory(inv.id)
        tx_count = len(InventoryTransaction.list_by_inventory(inv.id, limit=1))
        reasons = []
        if links:
            reasons.append(f'被 {len(links)} 个服务项目关联')
        if tx_count > 0:
            reasons.append(f'有 {tx_count} 条流水记录')
        if reasons:
            QMessageBox.warning(
                self, '无法删除',
                f'耗材「{inv.name}」无法删除：\n  • ' + '\n  • '.join(reasons)
                + '\n\n建议将耗材标记到备注中归档，历史记录仍可正常查看。'
            )
            return
        r = QMessageBox.question(self, '确认删除',
                                 f'确定删除耗材「{inv.name}」？\n该耗材无任何关联记录，删除后不可恢复。',
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            Inventory.delete(inv.id)
            self.refresh()

    def _on_edit_links(self, svc):
        d = ServiceLinkDialog(self, svc)
        if d.exec():
            self.refresh()


class ServiceLinkDialog(QDialog):
    def __init__(self, parent=None, svc=None):
        super().__init__(parent)
        self.svc = svc
        self.setWindowTitle(f'{svc.name} - 耗材关联' if svc else '耗材关联')
        self.resize(500, 500)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        tip = QLabel('勾选该服务需要消耗的耗材，并设置每次用量。')
        tip.setStyleSheet('color:#6b7280;')
        lay.addWidget(tip)

        self.items = []
        all_inv = Inventory.list()
        existing = ServiceInventoryLink.list_by_service(self.svc.id)
        existing_ids = {l['inventory_id']: l.get('quantity', 1) for l in existing}

        scroll = QWidget()
        scroll_lay = QVBoxLayout(scroll)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(8)
        for inv in all_inv:
            row = QHBoxLayout()
            row.setSpacing(10)
            cb = QComboBox()
            cb.addItem(f'⚪ 不关联', 0)
            cb.addItem(f'✅ 关联 (当前库存: {inv.stock})', 1)
            cb.setCurrentIndex(1 if inv.id in existing_ids else 0)
            cb.setFixedWidth(200)
            name = QLabel(f'{inv.name} [{inv.category}]')
            name.setStyleSheet('font-weight:bold;')
            name.setFixedWidth(180)
            sp_qty = QSpinBox()
            sp_qty.setRange(1, 99)
            sp_qty.setValue(existing_ids.get(inv.id, 1))
            sp_qty.setPrefix('每次用量: ')
            sp_qty.setSuffix(f' {inv.unit}')
            sp_qty.setFixedWidth(160)
            self.items.append({'inv': inv, 'cb': cb, 'qty': sp_qty})
            row.addWidget(name)
            row.addWidget(cb)
            row.addWidget(sp_qty)
            row.addStretch(1)
            w = QWidget()
            w.setLayout(row)
            scroll_lay.addWidget(w)
        scroll_lay.addStretch(1)

        from PyQt6.QtWidgets import QScrollArea
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(scroll)
        lay.addWidget(sa, 1)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton('保存')
        btn_ok.setStyleSheet(_btn_primary())
        btn_ok.clicked.connect(self._ok)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    def _ok(self):
        links = []
        for it in self.items:
            if it['cb'].currentData() == 1:
                links.append({'inventory_id': it['inv'].id, 'quantity': it['qty'].value()})
        ServiceInventoryLink.set_links(self.svc.id, links)
        self.accept()
