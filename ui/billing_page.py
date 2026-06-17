from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDateEdit, QMessageBox,
                             QFrame, QTextEdit, QDoubleSpinBox, QSpinBox, QFileDialog,
                             QGroupBox, QCheckBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from models import Bill, Appointment, Pet, Service, Member, Inventory
from modules import BillingEngine, PricingEngine


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:8px 20px;
            border-radius:6px; font-weight:bold; border:none; }
            QPushButton:hover { background:#f59e0b; }'''
def _btn_secondary():
    return '''QPushButton { background:#e5e7eb; color:#374151; padding:8px 20px;
            border-radius:6px; border:none; }
            QPushButton:hover { background:#d1d5db; }'''
def _btn_green():
    return '''QPushButton { background:#10b981; color:#fff; padding:8px 18px;
            border-radius:6px; font-weight:bold; border:none; }
            QPushButton:hover { background:#059669; }'''
def _btn_info():
    return '''QPushButton { background:#dbeafe; color:#1d4ed8; padding:6px 14px;
            border-radius:5px; border:none; }
            QPushButton:hover { background:#bfdbfe; }'''
def _line_style():
    return '''QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {
        padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
        background:#fff; font-size:13px; }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }'''


class GenerateBillDialog(QDialog):
    def __init__(self, parent=None, appointment=None):
        super().__init__(parent)
        self.appointment = appointment
        self._price_info = None
        self._member = None
        self.setWindowTitle('💸 生成账单')
        self.resize(480, 680)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        if self.appointment:
            info_box = QGroupBox('预约信息')
            info_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
            fl = QFormLayout(info_box)
            fl.setSpacing(8)
            pet = Pet.get(self.appointment.pet_id)
            svc = Service.get(self.appointment.service_id)
            fl.addRow('宠物:', QLabel(f'{pet.name if pet else "?"} ({pet.species if pet else ""})'))
            fl.addRow('主人:', QLabel(f'{pet.owner_name if pet else "-"} {pet.owner_phone if pet else ""}'))
            fl.addRow('项目:', QLabel(f'{svc.name if svc else "?"} ({svc.duration if svc else 0}分钟)'))
            fl.addRow('时段:', QLabel(f'{self.appointment.start_time} ~ {self.appointment.end_time}'))
            root.addWidget(info_box)

        member_box = QGroupBox('会员 & 支付方式')
        member_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        mf = QFormLayout(member_box)
        mf.setSpacing(10)
        self.cb_member = QComboBox()
        self.cb_member.addItem('— 非会员 —', None)
        default_member_id = None
        if self.appointment:
            pet = Pet.get(self.appointment.pet_id)
            if pet and pet.member_id:
                default_member_id = pet.member_id
        for m in Member.list():
            self.cb_member.addItem(f'{m.level} | {m.owner_name} ({m.owner_phone})', m.id)
        self.cb_member.currentIndexChanged.connect(self._on_member_changed)
        mf.addRow('会员:', self.cb_member)
        if default_member_id:
            for i in range(self.cb_member.count()):
                if self.cb_member.itemData(i) == default_member_id:
                    self.cb_member.setCurrentIndex(i)
                    break
        self.lbl_member_info = QLabel('')
        self.lbl_member_info.setStyleSheet('color:#2563eb; font-size:12px; padding:4px 0;')
        mf.addRow('', self.lbl_member_info)

        self.chk_use_balance = QCheckBox('使用会员余额抵扣')
        self.chk_use_balance.setStyleSheet('QCheckBox{font-weight:bold;}')
        self.chk_use_balance.toggled.connect(self._on_member_changed)
        mf.addRow('', self.chk_use_balance)

        self.sp_balance_used = QDoubleSpinBox()
        self.sp_balance_used.setRange(0, 99999)
        self.sp_balance_used.setDecimals(2)
        self.sp_balance_used.setPrefix('¥ ')
        self.sp_balance_used.valueChanged.connect(self._calc_pay)
        mf.addRow('余额抵扣:', self.sp_balance_used)

        self.lbl_points_preview = QLabel('')
        self.lbl_points_preview.setStyleSheet('color:#059669; font-size:12px; font-weight:bold; padding:2px 0;')
        mf.addRow('赠送积分:', self.lbl_points_preview)

        self.lbl_cash_pay = QLabel('')
        self.lbl_cash_pay.setStyleSheet('color:#ef4444; font-size:13px; font-weight:bold; padding:4px 0;')
        mf.addRow('现金/扫码支付:', self.lbl_cash_pay)
        root.addWidget(member_box)

        form_box = QGroupBox('计费参数')
        form_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        form = QFormLayout(form_box)
        form.setSpacing(10)
        self.sp_overtime = QSpinBox()
        self.sp_overtime.setRange(0, 600)
        self.sp_overtime.setSuffix(' 分钟')
        self.sp_overtime.valueChanged.connect(self._calc)
        form.addRow('超时时长:', self.sp_overtime)

        self.sp_discount = QDoubleSpinBox()
        self.sp_discount.setRange(0, 99999)
        self.sp_discount.setDecimals(2)
        self.sp_discount.setPrefix('¥ ')
        self.sp_discount.valueChanged.connect(self._calc)
        form.addRow('优惠折扣:', self.sp_discount)

        self.te_extra = QTextEdit()
        self.te_extra.setPlaceholderText('每行一个额外项目：项目名=金额，例如：\n指甲修剪=20\n耳道清洁=15')
        self.te_extra.setFixedHeight(60)
        self.te_extra.textChanged.connect(self._calc)
        form.addRow('额外项目:', self.te_extra)
        root.addWidget(form_box)

        self.lbl_inv_warn = QLabel('')
        self.lbl_inv_warn.setStyleSheet('color:#ef4444; font-weight:bold; font-size:13px; padding:6px 10px; background:#fef2f2; border-radius:6px;')
        self.lbl_inv_warn.setVisible(False)
        root.addWidget(self.lbl_inv_warn)

        price_box = QGroupBox('费用明细')
        price_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        self.pl = QFormLayout(price_box)
        self.pl.setSpacing(6)
        self.l_base = QLabel('—')
        self.l_cap = QLabel('—')
        self.l_ws = QLabel('—')
        self.l_sp = QLabel('—')
        self.l_ot = QLabel('—')
        self.l_ex = QLabel('—')
        self.l_disc = QLabel('—')
        self.l_final = QLabel('—')
        self.l_final.setStyleSheet('font-size:20px; font-weight:bold; color:#10b981;')
        self.l_note = QLabel('')
        self.l_note.setStyleSheet('color:#f59e0b; font-size:12px;')
        self.pl.addRow('起步价:', self.l_base)
        self.pl.addRow('封顶价:', self.l_cap)
        self.pl.addRow('体型加价:', self.l_ws)
        self.pl.addRow('物种加价:', self.l_sp)
        self.pl.addRow('超时费用:', self.l_ot)
        self.pl.addRow('额外项目:', self.l_ex)
        self.pl.addRow('折扣:', self.l_disc)
        self.pl.addRow('应付金额:', self.l_final)
        self.pl.addRow('', self.l_note)
        root.addWidget(price_box)

        btns = QHBoxLayout()
        btns.addStretch(1)
        b1 = QPushButton('取消')
        b1.setStyleSheet(_btn_secondary())
        b1.clicked.connect(self.reject)
        btns.addWidget(b1)
        b2 = QPushButton('✅ 生成账单')
        b2.setStyleSheet(_btn_primary())
        b2.clicked.connect(self._confirm)
        btns.addWidget(b2)
        root.addLayout(btns)

        self._calc()

    def _on_member_changed(self):
        mid = self.cb_member.currentData()
        if mid:
            m = Member.get(mid)
            self._member = m
            if m:
                self.lbl_member_info.setText(f'  余额 ¥{m.balance:.2f} · 积分 {m.points}')
                if not self.chk_use_balance.isChecked():
                    self.chk_use_balance.setChecked(True)
            else:
                self.lbl_member_info.setText('')
        else:
            self._member = None
            self.lbl_member_info.setText('')
        self._calc_pay()

    def _calc_pay(self):
        final = self._price_info['final_amount'] if self._price_info else 0
        if self._member:
            total_points = int(final)
            if self.chk_use_balance.isChecked():
                max_use = min(self._member.balance, final)
                if self.sp_balance_used.value() > self._member.balance + 0.01:
                    self.sp_balance_used.blockSignals(True)
                    self.sp_balance_used.setValue(max_use)
                    self.sp_balance_used.blockSignals(False)
                if self.sp_balance_used.value() < 0.01:
                    self.sp_balance_used.blockSignals(True)
                    self.sp_balance_used.setValue(max_use)
                    self.sp_balance_used.blockSignals(False)
                used = self.sp_balance_used.value()
                self.lbl_points_preview.setText(f'+{total_points} 积分（1元=1积分，按消费总额赠送）')
                self.lbl_cash_pay.setText(f'¥{max(0, final - used):.2f}')
                self.sp_balance_used.setEnabled(True)
            else:
                self.lbl_points_preview.setText(f'+{total_points} 积分（1元=1积分，按消费总额赠送）')
                self.lbl_cash_pay.setText(f'¥{final:.2f}')
                self.sp_balance_used.setValue(0)
                self.sp_balance_used.setEnabled(False)
        else:
            self.lbl_points_preview.setText('非会员无积分赠送')
            self.lbl_cash_pay.setText(f'¥{final:.2f}')
            self.sp_balance_used.setValue(0)
            self.sp_balance_used.setEnabled(False)

    def _parse_extra(self):
        items = {}
        txt = self.te_extra.toPlainText().strip()
        if not txt: return items
        for line in txt.split('\n'):
            line = line.strip()
            if '=' in line:
                k, v = line.rsplit('=', 1)
                try:
                    items[k.strip()] = float(v.strip())
                except: pass
        return items

    def _calc(self):
        if not self.appointment: return
        info, err = PricingEngine.calculate_price(
            self.appointment.service_id,
            self.appointment.pet_id,
            overtime_minutes=self.sp_overtime.value(),
            extra_items=self._parse_extra(),
            discount_amount=self.sp_discount.value()
        )
        self._price_info = info
        if info:
            self.l_base.setText(f'¥{info["base_price"]:.2f}')
            self.l_cap.setText(f'¥{info["cap_price"]:.2f}')
            self.l_ws.setText(f'+¥{info.get("weight_surcharge",0):.2f}' if info.get("weight_surcharge") else '¥0.00')
            self.l_sp.setText(f'+¥{info.get("species_surcharge",0):.2f}' if info.get("species_surcharge") else '¥0.00')
            self.l_ot.setText(f'+¥{info.get("overtime_surcharge",0):.2f}' if info.get("overtime_surcharge") else '¥0.00')
            self.l_ex.setText(f'+¥{info.get("extra_items_surcharge",0):.2f}' if info.get("extra_items_surcharge") else '¥0.00')
            self.l_disc.setText(f'-¥{info.get("discount_amount",0):.2f}' if info.get("discount_amount") else '¥0.00')
            self.l_final.setText(f'¥{info["final_amount"]:.2f}')
            notes = []
            if info.get('price_capped'):
                notes.append('🔒 已按封顶价拦截')
            if info.get('is_package'):
                notes.append('📦 套餐一口价')
            notes.extend(info.get('bound_warnings', []))
            self.l_note.setText(' | '.join(notes))
        # 检查库存
        ok, warns = Inventory.check_service_inventory(self.appointment.service_id)
        if not ok:
            self.lbl_inv_warn.setText('⚠️ 库存不足: ' + '，'.join(warns))
            self.lbl_inv_warn.setVisible(True)
        else:
            self.lbl_inv_warn.setVisible(False)
        self._calc_pay()

    def _confirm(self):
        if not self.appointment:
            QMessageBox.warning(self, '提示', '无效的预约信息')
            return
        if not self._price_info:
            QMessageBox.warning(self, '提示', '请先计算费用')
            return
        mid = self.cb_member.currentData()
        use_balance = self.chk_use_balance.isChecked()
        balance_used = self.sp_balance_used.value() if (mid and use_balance) else 0
        if mid and use_balance:
            m = Member.get(mid)
            if m and balance_used > m.balance + 0.01:
                QMessageBox.warning(self, '余额不足',
                                    f'会员 {m.owner_name} 当前余额 ¥{m.balance:.2f}，不足以抵扣 ¥{balance_used:.2f}')
                return
        bill, info = BillingEngine.generate_bill(
            self.appointment.id,
            overtime_minutes=self.sp_overtime.value(),
            extra_items=self._parse_extra(),
            discount_amount=self.sp_discount.value(),
            member_id=mid,
            balance_used=balance_used
        )
        if bill:
            self._saved_bill_id = bill.id
            receipt = BillingEngine.format_receipt(bill.id)
            self._show_receipt(receipt)
            self.accept()
        else:
            QMessageBox.warning(self, '生成失败', info or '未知错误')

    def _show_receipt(self, text):
        dlg = QDialog(self)
        dlg.setWindowTitle('🧾 账单已生成')
        dlg.resize(500, 680)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setStyleSheet('font-family: "Courier New", Consolas, monospace; font-size:13px; background:#fafafa; border:1px solid #e5e7eb; border-radius:6px; padding:10px;')
        te.setPlainText(text)
        lay.addWidget(te, 1)
        btns = QHBoxLayout()
        bs = QPushButton('💾 保存小票')
        bs.setStyleSheet(_btn_secondary())
        bill_id_ref = self._saved_bill_id
        def save():
            default_name = f'bill_B{bill_id_ref:08d}.txt'
            fn, _ = QFileDialog.getSaveFileName(dlg, '保存小票', default_name, '文本文件 (*.txt)')
            if fn:
                try:
                    with open(fn, 'w', encoding='utf-8') as f:
                        f.write(text)
                    QMessageBox.information(dlg, '成功', f'小票已保存至:\n{fn}')
                except Exception as e:
                    QMessageBox.warning(dlg, '保存失败', str(e))
        bs.clicked.connect(save)
        btns.addWidget(bs)
        btns.addStretch(1)
        bk = QPushButton('关闭')
        bk.setStyleSheet(_btn_primary())
        bk.clicked.connect(dlg.accept)
        btns.addWidget(bk)
        lay.addLayout(btns)
        dlg.exec()


class ReceiptDialog(QDialog):
    def __init__(self, parent, receipt_text, bill_id=None):
        super().__init__(parent)
        self.setWindowTitle('🧾 消费账单')
        self.resize(500, 680)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setStyleSheet('font-family: "Courier New", Consolas, monospace; font-size:13px; background:#fafafa; border:1px solid #e5e7eb; border-radius:6px; padding:10px;')
        te.setPlainText(receipt_text)
        lay.addWidget(te, 1)
        btns = QHBoxLayout()
        bs = QPushButton('💾 保存为文件')
        bs.setStyleSheet(_btn_secondary())
        def save():
            default_name = f'bill_B{bill_id:08d}.txt' if bill_id else 'bill_receipt.txt'
            fn, _ = QFileDialog.getSaveFileName(self, '保存小票', default_name, '文本文件 (*.txt)')
            if fn:
                try:
                    with open(fn, 'w', encoding='utf-8') as f:
                        f.write(receipt_text)
                    QMessageBox.information(self, '成功', f'小票已保存至:\n{fn}')
                except Exception as e:
                    QMessageBox.warning(self, '保存失败', str(e))
        bs.clicked.connect(save)
        btns.addWidget(bs)
        btns.addStretch(1)
        bk = QPushButton('关闭')
        bk.setStyleSheet(_btn_primary())
        bk.clicked.connect(self.accept)
        btns.addWidget(bk)
        lay.addLayout(btns)


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()
        self.setStyleSheet(_line_style())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        h = QLabel('💳 账单管理 · 起步价 / 封顶价计费')
        h.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(h)

        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet('background:#fff; padding:12px 18px; border-radius:8px; border:1px solid #e5e7eb; color:#374151; font-size:13px;')
        root.addWidget(self.lbl_stats)

        tb = QHBoxLayout()
        tb.setSpacing(12)
        self.de_from = QDateEdit()
        self.de_from.setCalendarPopup(True)
        self.de_from.setDate(QDate.currentDate().addDays(-30))
        self.de_from.setDisplayFormat('yyyy-MM-dd')
        self.de_from.dateChanged.connect(self.refresh)
        tb.addWidget(QLabel('开单从:'))
        tb.addWidget(self.de_from)
        self.de_to = QDateEdit()
        self.de_to.setCalendarPopup(True)
        self.de_to.setDate(QDate.currentDate())
        self.de_to.setDisplayFormat('yyyy-MM-dd')
        self.de_to.dateChanged.connect(self.refresh)
        tb.addWidget(QLabel('至:'))
        tb.addWidget(self.de_to)
        self.cb_paid = QComboBox()
        self.cb_paid.addItem('全部状态', None)
        self.cb_paid.addItem('待支付', 'unpaid')
        self.cb_paid.addItem('已结清', 'paid')
        self.cb_paid.addItem('已退款', 'refund')
        self.cb_paid.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_paid)
        tb.addStretch(1)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 宠物/主人/项目...')
        self.ed_search.returnPressed.connect(self.refresh)
        tb.addWidget(self.ed_search)
        btn_ref = QPushButton('🔄 刷新')
        btn_ref.setStyleSheet(_btn_secondary())
        btn_ref.clicked.connect(self.refresh)
        tb.addWidget(btn_ref)
        btn_new = QPushButton('➕ 从预约开单')
        btn_new.setStyleSheet(_btn_primary())
        btn_new.clicked.connect(self._on_generate)
        tb.addWidget(btn_new)
        root.addLayout(tb)

        self.table = QTableWidget()
        self.table.setStyleSheet('''
            QTableWidget { background:#fff; border-radius:8px; border:1px solid #e5e7eb; gridline-color:#f3f4f6; }
            QTableWidget::item { padding: 6px 10px; }
            QHeaderView::section { background:#f9fafb; padding:10px; border:none; border-bottom:2px solid #e5e7eb; color:#374151; font-weight:bold; }
        ''')
        hd = ['ID', '开单时间', '宠物', '会员', '项目', '原价', '抵扣', '实付', '积分', '状态', '操作']
        self.table.setColumnCount(len(hd))
        self.table.setHorizontalHeaderLabels(hd)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.lbl = QLabel('共 0 条账单')
        self.lbl.setStyleSheet('color:#6b7280; font-size:12px;')
        root.addWidget(self.lbl)

    def refresh(self):
        df = self.de_from.date().toString('yyyy-MM-dd')
        dt = self.de_to.date().toString('yyyy-MM-dd')
        ps = self.cb_paid.currentData()
        kw = self.ed_search.text().strip() or None
        bills = BillingEngine.list_bills(ps, df, dt, kw)
        stats = BillingEngine.get_dashboard_stats(df, dt)
        self.lbl_stats.setText(
            f'📈 区间统计: 共 {stats.get("bill_count",0)} 单 · '
            f'总金额 ¥{stats.get("total_amount",0):.2f} · '
            f'已收 ¥{stats.get("paid_total",0):.2f} · '
            f'待收 ¥{stats.get("unpaid_total",0):.2f}  |  '
            f'👥 会员储值 ¥{stats.get("member_total_balance",0):.2f} · '
            f'📦 低库存 {stats.get("low_stock_count",0)} 项 · '
            f'🧴 近7天耗材 ¥{stats.get("inv_consumed_value_7d",0):.2f}'
        )
        self.table.setRowCount(len(bills))
        status_map = {
            'unpaid': ('⏳待支付', '#f59e0b'),
            'paid': ('✅已结清', '#10b981'),
            'refund': ('↩️已退款', '#6b7280')
        }
        for row, b in enumerate(bills):
            member_name = b.get('member_name', '') or '非会员'
            vals = [
                f'B{b["id"]:08d}',
                (b['created_at'] or '').split('.')[0][:16],
                b.get('pet_name', ''),
                member_name,
                b.get('service_name', ''),
                f'¥{b["base_amount"]:.2f}',
                f'-¥{b.get("balance_used",0):.2f}' if b.get("balance_used") else '-',
                f'¥{b["final_amount"]:.2f}',
                f'+{b.get("points_awarded",0)}' if b.get("points_awarded") else '-',
                status_map.get(b['paid_status'], (b['paid_status'], '#000'))[0]
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 9:
                    it.setForeground(QColor(status_map.get(b['paid_status'], ('', '#000'))[1]))
                if c == 7:
                    f = self.table.font()
                    f.setBold(True)
                    it.setFont(f)
                if c == 3 and b.get("member_name"):
                    it.setForeground(QColor('#2563eb'))
                self.table.setItem(row, c, it)

            opf = QFrame()
            ol = QHBoxLayout(opf)
            ol.setContentsMargins(4, 3, 4, 3)
            ol.setSpacing(4)
            bprint = QPushButton('小票')
            bprint.setStyleSheet(_btn_info())
            bprint.clicked.connect(lambda _, _id=b['id']: self._on_receipt(_id))
            ol.addWidget(bprint)
            if b['paid_status'] == 'unpaid':
                bpay = QPushButton('收款')
                bpay.setStyleSheet(_btn_green())
                bpay.clicked.connect(lambda _, _id=b['id']: self._on_pay(_id))
                ol.addWidget(bpay)
            self.table.setCellWidget(row, 10, opf)
            self.table.setRowHeight(row, 42)
        self.lbl.setText(f'共 {len(bills)} 条账单记录')

    def _on_generate(self):
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        rows = Appointment.list_by_date(today)
        pending = [r for r in rows if r['status'] == 'completed']
        if not pending:
            pending = [r for r in rows if r['status'] in ('confirmed', 'pending')]
        if not pending:
            QMessageBox.information(self, '提示', '今日暂无待开单的预约')
            return
        dlg = QDialog(self)
        dlg.setWindowTitle('选择预约开单')
        dlg.resize(640, 480)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.addWidget(QLabel('选择要生成账单的预约：'))
        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(['预约ID', '时段', '宠物', '项目', '工位'])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setRowCount(len(pending))
        for r, p in enumerate(pending):
            tbl.setItem(r, 0, QTableWidgetItem(str(p['id'])))
            tbl.setItem(r, 1, QTableWidgetItem(f"{p['start_time'].split()[1]}~{p['end_time'].split()[1]}"))
            tbl.setItem(r, 2, QTableWidgetItem(p.get('pet_name', '')))
            tbl.setItem(r, 3, QTableWidgetItem(p.get('service_name', '')))
            tbl.setItem(r, 4, QTableWidgetItem(p.get('ws_name', '-')))
        lay.addWidget(tbl, 1)
        btns = QHBoxLayout()
        btns.addStretch(1)
        b1 = QPushButton('取消')
        b1.setStyleSheet(_btn_secondary())
        b1.clicked.connect(dlg.reject)
        btns.addWidget(b1)
        b2 = QPushButton('下一步：计费开单')
        b2.setStyleSheet(_btn_primary())
        def _next():
            r = tbl.currentRow()
            if r < 0:
                QMessageBox.warning(dlg, '提示', '请选择一条预约')
                return
            appt = Appointment.get(int(pending[r]['id']))
            dlg.accept()
            gd = GenerateBillDialog(self, appt)
            if gd.exec():
                self.refresh()
        b2.clicked.connect(_next)
        btns.addWidget(b2)
        lay.addLayout(btns)
        dlg.exec()

    def _on_pay(self, bill_id):
        b, err = BillingEngine.mark_bill_paid(bill_id)
        if b:
            QMessageBox.information(self, '收款成功', f'账单 B{bill_id:08d} 已结清 ¥{b.final_amount:.2f}')
            self.refresh()
        else:
            QMessageBox.warning(self, '失败', err or '操作失败')

    def _on_receipt(self, bill_id):
        txt = BillingEngine.format_receipt(bill_id)
        ReceiptDialog(self, txt, bill_id).exec()
