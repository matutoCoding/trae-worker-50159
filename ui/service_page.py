from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QMessageBox, QFrame, QCheckBox)
from PyQt6.QtCore import Qt
from models import Service, Appointment
from modules import PricingEngine


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:8px 20px;
            border-radius:6px; font-weight:bold; border:none; }
            QPushButton:hover { background:#f59e0b; }'''
def _btn_secondary():
    return '''QPushButton { background:#e5e7eb; color:#374151; padding:8px 20px;
            border-radius:6px; border:none; }
            QPushButton:hover { background:#d1d5db; }'''
def _btn_danger():
    return '''QPushButton { background:#fee2e2; color:#b91c1c; padding:6px 14px;
            border-radius:5px; border:none; }
            QPushButton:hover { background:#fecaca; }'''
def _line_style():
    return '''QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
        padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
        background:#fff; font-size:13px; }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }'''


class ServiceFormDialog(QDialog):
    CATEGORIES = ['清洁类', '修剪类', 'SPA类', '医疗类', '套餐', '其他']

    def __init__(self, parent=None, svc=None):
        super().__init__(parent)
        self.svc = svc
        self.setWindowTitle('美容项目建档' if not svc else '编辑美容项目')
        self.resize(480, 520)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.ed_name = QLineEdit()
        form.addRow('项目名称*:', self.ed_name)
        self.cb_cat = QComboBox()
        self.cb_cat.addItems(self.CATEGORIES)
        form.addRow('分类*:', self.cb_cat)
        self.sp_dur = QSpinBox()
        self.sp_dur.setRange(5, 480)
        self.sp_dur.setSuffix(' 分钟')
        self.sp_dur.setValue(60)
        form.addRow('服务时长*:', self.sp_dur)
        self.sp_base = QDoubleSpinBox()
        self.sp_base.setRange(0, 9999)
        self.sp_base.setDecimals(2)
        self.sp_base.setPrefix('¥ ')
        self.sp_base.setValue(68)
        form.addRow('起步价*:', self.sp_base)
        self.sp_cap = QDoubleSpinBox()
        self.sp_cap.setRange(0, 9999)
        self.sp_cap.setDecimals(2)
        self.sp_cap.setPrefix('¥ ')
        self.sp_cap.setValue(88)
        form.addRow('封顶价*:', self.sp_cap)
        self.chk_pkg = QCheckBox('是套餐项目（起步价=封顶价）')
        self.chk_pkg.toggled.connect(self._on_pkg)
        form.addRow('套餐:', self.chk_pkg)
        self.sp_base.valueChanged.connect(self._on_base_changed)
        self.te_desc = QTextEdit()
        self.te_desc.setFixedHeight(80)
        self.te_desc.setPlaceholderText('服务描述、包含内容...')
        form.addRow('描述:', self.te_desc)
        self.lbl_validate = QLabel('')
        self.lbl_validate.setWordWrap(True)
        self.lbl_validate.setStyleSheet('color:#ef4444; font-size:12px; min-height:30px;')
        form.addRow('', self.lbl_validate)
        root.addLayout(form)

        btns = QHBoxLayout()
        bp = QPushButton('💸 预览计费')
        bp.setStyleSheet(_btn_secondary())
        bp.clicked.connect(self._preview)
        btns.addWidget(bp)
        btns.addStretch(1)
        b1 = QPushButton('取消')
        b1.setStyleSheet(_btn_secondary())
        b1.clicked.connect(self.reject)
        btns.addWidget(b1)
        b2 = QPushButton('💾 保存')
        b2.setStyleSheet(_btn_primary())
        b2.clicked.connect(self._save)
        btns.addWidget(b2)
        root.addLayout(btns)

        if self.svc:
            self.ed_name.setText(self.svc.name or '')
            i = self.cb_cat.findText(self.svc.category)
            if i >= 0: self.cb_cat.setCurrentIndex(i)
            self.sp_dur.setValue(self.svc.duration or 60)
            self.sp_base.setValue(self.svc.base_price or 0)
            self.sp_cap.setValue(self.svc.cap_price or 0)
            self.chk_pkg.setChecked(bool(self.svc.is_package))
            self.te_desc.setPlainText(self.svc.description or '')

    def _on_pkg(self, checked):
        if checked:
            self.sp_cap.setValue(self.sp_base.value())
            self.sp_cap.setEnabled(False)
        else:
            self.sp_cap.setEnabled(True)

    def _on_base_changed(self, val):
        if self.chk_pkg.isChecked():
            self.sp_cap.blockSignals(True)
            self.sp_cap.setValue(val)
            self.sp_cap.blockSignals(False)

    def _preview(self):
        errs = PricingEngine.validate_service_pricing(
            self.sp_base.value(), self.sp_cap.value(), self.chk_pkg.isChecked()
        )
        self.lbl_validate.setText('\n'.join(errs))
        if errs:
            return
        QMessageBox.information(
            self, '计费预览',
            f'项目类型: {"套餐" if self.chk_pkg.isChecked() else "标准项目"}\n'
            f'起步价: ¥{self.sp_base.value():.2f}\n'
            f'封顶价: ¥{self.sp_cap.value():.2f}\n'
            f'时长: {self.sp_dur.value()} 分钟\n\n'
            f'规则说明:\n'
            f'• 简单项目按起步价收取\n'
            f'• 有超重/超时等附加费时累计，但不超过封顶价\n'
            f'• 套餐按封顶价一口价计费'
        )

    def _save(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, '提示', '请填写项目名称')
            return
        errs = PricingEngine.validate_service_pricing(
            self.sp_base.value(), self.sp_cap.value(), self.chk_pkg.isChecked()
        )
        if errs:
            self.lbl_validate.setText('\n'.join(errs))
            QMessageBox.warning(self, '价格校验失败', '\n'.join(errs))
            return
        self.result = {
            'name': name, 'category': self.cb_cat.currentText(),
            'duration': self.sp_dur.value(),
            'base_price': self.sp_base.value(),
            'cap_price': self.sp_cap.value(),
            'description': self.te_desc.toPlainText().strip(),
            'is_package': 1 if self.chk_pkg.isChecked() else 0
        }
        self.accept()


class ServicePage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()
        self.setStyleSheet(_line_style())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)
        h = QLabel('✂️ 美容服务项目与计费规则')
        h.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(h)

        tb = QHBoxLayout()
        tb.setSpacing(12)
        self.cb_cat = QComboBox()
        self.cb_cat.addItem('全部分类', None)
        for c in ServiceFormDialog.CATEGORIES:
            self.cb_cat.addItem(c, c)
        self.cb_cat.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_cat)
        self.cb_pkg = QComboBox()
        self.cb_pkg.addItem('全部项目', None)
        self.cb_pkg.addItem('标准项目', False)
        self.cb_pkg.addItem('仅套餐', True)
        self.cb_pkg.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_pkg)
        tb.addStretch(1)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 搜索项目名称/描述...')
        self.ed_search.returnPressed.connect(self.refresh)
        tb.addWidget(self.ed_search)
        btn = QPushButton('➕ 新建服务项目')
        btn.setStyleSheet(_btn_primary())
        btn.clicked.connect(self._on_add)
        tb.addWidget(btn)
        root.addLayout(tb)

        self.table = QTableWidget()
        self.table.setStyleSheet('''
            QTableWidget { background:#fff; border-radius:8px; border:1px solid #e5e7eb; gridline-color:#f3f4f6; }
            QTableWidget::item { padding: 6px 10px; }
            QHeaderView::section { background:#f9fafb; padding:10px; border:none; border-bottom:2px solid #e5e7eb; color:#374151; font-weight:bold; }
        ''')
        hd = ['ID', '项目名', '分类', '类型', '时长', '起步价', '封顶价', '定价', '描述', '操作']
        self.table.setColumnCount(len(hd))
        self.table.setHorizontalHeaderLabels(hd)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.lbl = QLabel('共 0 个服务项目')
        self.lbl.setStyleSheet('color:#6b7280; font-size:12px;')
        root.addWidget(self.lbl)

    def refresh(self):
        c = self.cb_cat.currentData()
        p = self.cb_pkg.currentData()
        kw = self.ed_search.text().strip()
        items = Service.list(category=c, is_package=p)
        if kw:
            items = [i for i in items if kw in (i.name or '') or kw in (i.description or '')]
        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            diff = s.cap_price - s.base_price
            if s.is_package:
                price_display = f'¥{s.base_price:.2f} 一口价'
            else:
                price_display = f'¥{s.base_price:.2f} ~ ¥{s.cap_price:.2f}'
            vals = [
                str(s.id), s.name, s.category,
                '📦 套餐' if s.is_package else '🧴 标准',
                f'{s.duration} 分钟',
                f'¥{s.base_price:.2f}',
                f'¥{s.cap_price:.2f}',
                price_display
            ]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if col == 3 and s.is_package:
                    it.setForeground(Qt.GlobalColor.darkMagenta)
                self.table.setItem(row, col, it)
            desc = QTableWidgetItem(s.description or '-')
            desc.setToolTip(s.description or '')
            self.table.setItem(row, 8, desc)

            opf = QFrame()
            ol = QHBoxLayout(opf)
            ol.setContentsMargins(6, 3, 6, 3)
            ol.setSpacing(6)
            be = QPushButton('编辑')
            be.setStyleSheet(_btn_secondary())
            be.clicked.connect(lambda _, _s=s: self._on_edit(_s))
            bd = QPushButton('删除')
            bd.setStyleSheet(_btn_danger())
            bd.clicked.connect(lambda _, _s=s: self._on_del(_s))
            ol.addStretch(1)
            ol.addWidget(be)
            ol.addWidget(bd)
            self.table.setCellWidget(row, 9, opf)
            self.table.setRowHeight(row, 42)
        self.lbl.setText(f'共 {len(items)} 个服务项目 · 套餐 {sum(1 for i in items if i.is_package)} 个')

    def _on_add(self):
        d = ServiceFormDialog(self)
        if d.exec():
            Service.add(d.result)
            self.refresh()

    def _on_edit(self, s):
        d = ServiceFormDialog(self, s)
        if d.exec():
            Service.update(s.id, d.result)
            self.refresh()

    def _on_del(self, s):
        appt_count = Appointment.count_by_service(s.id)
        if appt_count > 0:
            QMessageBox.warning(
                self, '无法删除',
                f'服务项目「{s.name}」仍有 {appt_count} 条有效预约记录，无法删除。\n\n'
                f'如需停用，可编辑该项目的描述标注"已停用"，现有预约和账单仍可正常查看。'
            )
            return
        r = QMessageBox.question(self, '确认删除', f'确定删除服务「{s.name}」？\n该项目暂无有效预约，删除后不可恢复。',
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            Service.delete(s.id)
            self.refresh()
