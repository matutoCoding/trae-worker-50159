from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QSpinBox, QTextEdit, QMessageBox, QFrame, QSizePolicy,
                             QTabWidget, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from models import Pet, Appointment, Bill, Member, MemberTransaction


def _btn_primary():
    return '''
        QPushButton { background:#fbbf24; color:#1f2937; padding:8px 20px;
            border-radius:6px; font-weight:bold; border:none; }
        QPushButton:hover { background:#f59e0b; }
    '''

def _btn_secondary():
    return '''
        QPushButton { background:#e5e7eb; color:#374151; padding:8px 20px;
            border-radius:6px; border:none; }
        QPushButton:hover { background:#d1d5db; }
    '''

def _btn_danger():
    return '''
        QPushButton { background:#fee2e2; color:#b91c1c; padding:6px 14px;
            border-radius:5px; border:none; }
        QPushButton:hover { background:#fecaca; }
    '''

def _btn_success():
    return '''
        QPushButton { background:#10b981; color:#fff; padding:6px 14px;
            border-radius:5px; border:none; font-weight:bold; }
        QPushButton:hover { background:#059669; }
    '''

def _line_edit_style():
    return '''
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
            padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
            background:#fff; font-size:13px;
        }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }
    '''


class PetFormDialog(QDialog):
    def __init__(self, parent=None, pet=None):
        super().__init__(parent)
        self.pet = pet
        self.setWindowTitle('宠物档案' if not pet else '编辑宠物档案')
        self.resize(480, 560)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText('请输入宠物名字')
        form.addRow('宠物名称*:', self.ed_name)

        self.cb_species = QComboBox()
        self.cb_species.addItems(['犬', '猫', '兔', '鸟', '其他'])
        form.addRow('物种*:', self.cb_species)

        self.ed_breed = QLineEdit()
        self.ed_breed.setPlaceholderText('如：金毛、英短蓝猫')
        form.addRow('品种:', self.ed_breed)

        self.sp_weight = QDoubleSpinBox()
        self.sp_weight.setRange(0, 200)
        self.sp_weight.setSuffix(' kg')
        self.sp_weight.setDecimals(1)
        form.addRow('体重:', self.sp_weight)

        self.sp_age = QSpinBox()
        self.sp_age.setRange(0, 30)
        self.sp_age.setSuffix(' 岁')
        form.addRow('年龄:', self.sp_age)

        self.ed_owner = QLineEdit()
        self.ed_owner.setPlaceholderText('请输入宠主姓名')
        form.addRow('宠主姓名*:', self.ed_owner)

        self.ed_phone = QLineEdit()
        self.ed_phone.setPlaceholderText('请输入联系电话')
        self.ed_phone.editingFinished.connect(self._auto_lookup_member)
        form.addRow('联系电话*:', self.ed_phone)

        self.cb_member = QComboBox()
        self.cb_member.addItem('— 非会员 —', None)
        for m in Member.list():
            self.cb_member.addItem(f'{m.level} | {m.owner_name} ({m.owner_phone}) 余额¥{m.balance:.2f}', m.id)
        self.cb_member.currentIndexChanged.connect(self._on_member_changed)
        form.addRow('关联会员:', self.cb_member)

        self.member_info = QLabel()
        self.member_info.setStyleSheet('color:#2563eb; font-size:12px; padding:4px 0;')
        self.member_info.setVisible(False)
        form.addRow('', self.member_info)

        self.te_notes = QTextEdit()
        self.te_notes.setPlaceholderText('宠物性格、病史、注意事项等')
        self.te_notes.setFixedHeight(80)
        form.addRow('备注:', self.te_notes)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        btn_cancel = QPushButton('取消')
        btn_cancel.setStyleSheet(_btn_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_save = QPushButton('💾 保存档案')
        btn_save.setStyleSheet(_btn_primary())
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        if self.pet:
            self.ed_name.setText(self.pet.name or '')
            idx = self.cb_species.findText(self.pet.species or '犬')
            if idx >= 0:
                self.cb_species.setCurrentIndex(idx)
            self.ed_breed.setText(self.pet.breed or '')
            self.sp_weight.setValue(self.pet.weight or 0)
            self.sp_age.setValue(self.pet.age or 0)
            self.ed_owner.setText(self.pet.owner_name or '')
            self.ed_phone.setText(self.pet.owner_phone or '')
            self.te_notes.setPlainText(self.pet.notes or '')
            if self.pet.member_id:
                for i in range(self.cb_member.count()):
                    if self.cb_member.itemData(i) == self.pet.member_id:
                        self.cb_member.setCurrentIndex(i)
                        break
                self._on_member_changed(self.cb_member.currentIndex())

    def _auto_lookup_member(self):
        phone = self.ed_phone.text().strip()
        if not phone:
            return
        for i in range(self.cb_member.count()):
            data = self.cb_member.itemData(i)
            text = self.cb_member.itemText(i)
            if data and phone in text:
                self.cb_member.setCurrentIndex(i)
                self._on_member_changed(i)
                return

    def _on_member_changed(self, idx):
        mid = self.cb_member.itemData(idx)
        if mid:
            m = Member.get(mid)
            if m:
                self.member_info.setText(f'  会员: {m.level} | 余额 ¥{m.balance:.2f} | 积分 {m.points}')
                self.member_info.setVisible(True)
                if not self.ed_owner.text().strip():
                    self.ed_owner.setText(m.owner_name)
                return
        self.member_info.setVisible(False)

    def _on_save(self):
        name = self.ed_name.text().strip()
        owner = self.ed_owner.text().strip()
        phone = self.ed_phone.text().strip()
        if not name or not owner or not phone:
            QMessageBox.warning(self, '提示', '请填写必填项：宠物名称、宠主姓名、联系电话')
            return
        mid = self.cb_member.currentData()
        self.result_data = {
            'name': name,
            'species': self.cb_species.currentText(),
            'breed': self.ed_breed.text().strip(),
            'weight': self.sp_weight.value(),
            'age': self.sp_age.value(),
            'owner_name': owner,
            'owner_phone': phone,
            'notes': self.te_notes.toPlainText().strip(),
            'member_id': mid
        }
        self.accept()


class RechargeDialog(QDialog):
    def __init__(self, parent=None, member=None):
        super().__init__(parent)
        self.member = member
        self.result_data = {}
        self.setWindowTitle(f'会员充值 - {member.owner_name}' if member else '会员充值')
        self.resize(360, 280)
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


class PetPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        header_row = QHBoxLayout()
        header = QLabel('🐕 宠物档案管理')
        header.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        header_row.addWidget(header)
        header_row.addStretch(1)
        self.lbl_member_stat = QLabel()
        self.lbl_member_stat.setStyleSheet('color:#2563eb; font-size:13px; padding:4px 12px;')
        header_row.addWidget(self.lbl_member_stat)
        root.addLayout(header_row)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 搜索宠物名/宠主/电话...')
        self.ed_search.setStyleSheet(_line_edit_style() + 'QLineEdit { padding:9px 14px; }')
        self.ed_search.returnPressed.connect(self.refresh)
        toolbar.addWidget(self.ed_search, 1)
        btn_search = QPushButton('搜索')
        btn_search.setStyleSheet(_btn_secondary())
        btn_search.clicked.connect(self.refresh)
        toolbar.addWidget(btn_search)
        btn_add = QPushButton('➕ 新建宠物档案')
        btn_add.setStyleSheet(_btn_primary())
        btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(btn_add)
        root.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setStyleSheet('''
            QTableWidget {
                background:#fff; border-radius:8px; border:1px solid #e5e7eb;
                gridline-color:#f3f4f6;
            }
            QTableWidget::item { padding: 6px 10px; }
            QHeaderView::section {
                background:#f9fafb; padding:10px; border:none;
                border-bottom:2px solid #e5e7eb; color:#374151; font-weight:bold;
            }
        ''')
        headers = ['ID', '宠物名', '物种', '品种', '宠主', '电话', '会员', '余额', '积分', '建档时间', '操作']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self.lbl_count = QLabel('共 0 只宠物')
        self.lbl_count.setStyleSheet('color:#6b7280; font-size:12px;')
        root.addWidget(self.lbl_count)

        self.setStyleSheet(_line_edit_style())

    def refresh(self):
        kw = self.ed_search.text().strip()
        pets = Pet.list(kw or None)
        self.table.setRowCount(len(pets))
        member_count = 0
        total_balance = 0
        for row, p in enumerate(pets):
            member = p.get_member()
            if member:
                member_count += 1
                total_balance += member.balance
                member_txt = member.level
                balance_txt = f'¥{member.balance:.2f}'
                points_txt = str(member.points)
            else:
                member_txt = '—'
                balance_txt = '—'
                points_txt = '—'
            items = [
                str(p.id), p.name, p.species, p.breed or '-',
                p.owner_name, p.owner_phone,
                member_txt, balance_txt, points_txt,
                (p.created_at or '').split('.')[0]
            ]
            for col, val in enumerate(items):
                it = QTableWidgetItem(val)
                if col == 1:
                    it.setForeground(Qt.GlobalColor.darkBlue)
                if col == 6 and member:
                    it.setForeground(Qt.GlobalColor.darkBlue)
                    it.setText(f'⭐ {member_txt}')
                self.table.setItem(row, col, it)

            op_frame = QFrame()
            op_layout = QHBoxLayout(op_frame)
            op_layout.setContentsMargins(4, 2, 4, 2)
            op_layout.setSpacing(4)
            if member:
                btn_recharge = QPushButton('充值')
                btn_recharge.setStyleSheet(_btn_success())
                btn_recharge.clicked.connect(lambda _, _m=member, _p=p: self._on_recharge(_m, _p))
                op_layout.addWidget(btn_recharge)
            btn_edit = QPushButton('编辑')
            btn_edit.setStyleSheet(_btn_secondary())
            btn_edit.clicked.connect(lambda _, _p=p: self._on_edit(_p))
            btn_del = QPushButton('删除')
            btn_del.setStyleSheet(_btn_danger())
            btn_del.clicked.connect(lambda _, _p=p: self._on_delete(_p))
            op_layout.addStretch(1)
            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 10, op_frame)
            self.table.setRowHeight(row, 42)

        self.lbl_count.setText(f'共 {len(pets)} 只宠物档案，其中会员宠物 {member_count} 只')
        self.lbl_member_stat.setText(f'会员储值余额合计: ¥{total_balance:.2f}')

    def _on_add(self):
        dlg = PetFormDialog(self)
        if dlg.exec():
            Pet.add(dlg.result_data)
            self.refresh()

    def _on_edit(self, pet):
        dlg = PetFormDialog(self, pet)
        if dlg.exec():
            Pet.update(pet.id, dlg.result_data)
            self.refresh()

    def _on_recharge(self, member, pet):
        dlg = RechargeDialog(self, member)
        if dlg.exec():
            m, err = Member.recharge(member.id, dlg.result_data['amount'], dlg.result_data['note'])
            if err:
                QMessageBox.warning(self, '充值失败', err)
            else:
                QMessageBox.information(self, '充值成功',
                                        f'会员 {m.owner_name} 充值成功\n当前余额: ¥{m.balance:.2f}')
            self.refresh()

    def _on_delete(self, pet):
        active_appt = Appointment.count_by_pet(pet.id)
        all_appt = Appointment.count_all_by_pet(pet.id)
        bill_count = Bill.count_by_pet(pet.id)
        total_links = all_appt + bill_count

        if total_links > 0:
            if active_appt > 0:
                msg = f'宠物「{pet.name}」仍有 {active_appt} 条有效预约，无法删除。'
            elif all_appt > 0:
                msg = f'宠物「{pet.name}」有 {all_appt} 条历史预约（含已取消），无法删除。'
            else:
                msg = f'宠物「{pet.name}」有 {bill_count} 条账单记录，无法删除。'
            QMessageBox.warning(
                self, '无法删除',
                f'{msg}\n\n如需归档，请将宠物备注中标注"已归档"，相关预约和账单仍可正常查看。'
            )
            return
        r = QMessageBox.question(
            self, '确认删除',
            f'确定删除宠物「{pet.name}」的档案吗？\n该宠物无任何关联记录，删除后不可恢复。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if r == QMessageBox.StandardButton.Yes:
            Pet.delete(pet.id)
            self.refresh()
