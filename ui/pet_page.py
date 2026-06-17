from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QSpinBox, QTextEdit, QMessageBox, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt
from models import Pet, Appointment


class PetFormDialog(QDialog):
    def __init__(self, parent=None, pet=None):
        super().__init__(parent)
        self.pet = pet
        self.setWindowTitle('宠物档案' if not pet else '编辑宠物档案')
        self.resize(460, 500)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

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
        form.addRow('联系电话*:', self.ed_phone)

        self.te_notes = QTextEdit()
        self.te_notes.setPlaceholderText('宠物性格、病史、注意事项等')
        self.te_notes.setFixedHeight(90)
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

    def _on_save(self):
        name = self.ed_name.text().strip()
        owner = self.ed_owner.text().strip()
        phone = self.ed_phone.text().strip()
        if not name or not owner or not phone:
            QMessageBox.warning(self, '提示', '请填写必填项：宠物名称、宠主姓名、联系电话')
            return
        self.result_data = {
            'name': name,
            'species': self.cb_species.currentText(),
            'breed': self.ed_breed.text().strip(),
            'weight': self.sp_weight.value(),
            'age': self.sp_age.value(),
            'owner_name': owner,
            'owner_phone': phone,
            'notes': self.te_notes.toPlainText().strip()
        }
        self.accept()


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

def _line_edit_style():
    return '''
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
            background:#fff; font-size:13px;
        }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }
    '''


class PetPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        header = QLabel('🐕 宠物档案管理')
        header.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(header)

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
        headers = ['ID', '宠物名', '物种', '品种', '体重', '年龄', '宠主', '电话', '建档时间', '操作']
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
        for row, p in enumerate(pets):
            items = [
                str(p.id), p.name, p.species, p.breed or '-',
                f'{p.weight}kg' if p.weight else '-',
                f'{p.age}岁' if p.age else '-',
                p.owner_name, p.owner_phone,
                (p.created_at or '').split('.')[0]
            ]
            for col, val in enumerate(items):
                it = QTableWidgetItem(val)
                if col == 1:
                    it.setForeground(Qt.GlobalColor.darkBlue)
                self.table.setItem(row, col, it)

            op_frame = QFrame()
            op_layout = QHBoxLayout(op_frame)
            op_layout.setContentsMargins(6, 3, 6, 3)
            op_layout.setSpacing(6)
            btn_edit = QPushButton('编辑')
            btn_edit.setStyleSheet(_btn_secondary())
            btn_edit.clicked.connect(lambda _, _p=p: self._on_edit(_p))
            btn_del = QPushButton('删除')
            btn_del.setStyleSheet(_btn_danger())
            btn_del.clicked.connect(lambda _, _p=p: self._on_delete(_p))
            op_layout.addStretch(1)
            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 9, op_frame)
            self.table.setRowHeight(row, 42)

        self.lbl_count.setText(f'共 {len(pets)} 只宠物档案')

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

    def _on_delete(self, pet):
        appt_count = Appointment.count_by_pet(pet.id)
        if appt_count > 0:
            QMessageBox.warning(
                self, '无法删除',
                f'宠物「{pet.name}」仍有 {appt_count} 条有效预约记录，无法删除。\n\n'
                f'如需归档，请将宠物备注中标注"已归档"，相关预约和账单仍可正常查看。'
            )
            return
        r = QMessageBox.question(
            self, '确认删除',
            f'确定删除宠物「{pet.name}」的档案吗？\n该宠物暂无有效预约，删除后不可恢复。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if r == QMessageBox.StandardButton.Yes:
            Pet.delete(pet.id)
            self.refresh()
