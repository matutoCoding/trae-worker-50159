from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QSpinBox, QTextEdit,
                             QMessageBox, QFrame, QProgressBar)
from PyQt6.QtCore import Qt
from models import Workstation
from modules import Scheduling


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
    return '''QLineEdit, QComboBox, QSpinBox, QTextEdit {
        padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
        background:#fff; font-size:13px; }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }'''


class WorkstationFormDialog(QDialog):
    TYPES = ['标准美容', 'SPA护理', '特殊美容', '其他']

    def __init__(self, parent=None, ws=None):
        super().__init__(parent)
        self.ws = ws
        self.setWindowTitle('工位资源建档' if not ws else '编辑工位')
        self.resize(440, 400)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(14)
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText('如：A1-美容台')
        form.addRow('工位名称*:', self.ed_name)
        self.cb_type = QComboBox()
        self.cb_type.addItems(self.TYPES)
        form.addRow('工位类型*:', self.cb_type)
        self.sp_cap = QSpinBox()
        self.sp_cap.setRange(1, 10)
        self.sp_cap.setSuffix(' 只')
        form.addRow('容量:', self.sp_cap)
        self.te_equip = QTextEdit()
        self.te_equip.setFixedHeight(80)
        self.te_equip.setPlaceholderText('配备设备，如：升降台,吹水机,臭氧机')
        form.addRow('设备配置:', self.te_equip)
        self.cb_status = QComboBox()
        self.cb_status.addItems(['active 启用', 'maintenance 维护', 'offline 停用'])
        form.addRow('状态:', self.cb_status)
        root.addLayout(form)

        btns = QHBoxLayout()
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

        if self.ws:
            self.ed_name.setText(self.ws.name or '')
            i = self.cb_type.findText(self.ws.type)
            if i >= 0: self.cb_type.setCurrentIndex(i)
            self.sp_cap.setValue(self.ws.capacity or 1)
            self.te_equip.setPlainText(self.ws.equipment or '')
            s_map = {'active': 0, 'maintenance': 1, 'offline': 2}
            self.cb_status.setCurrentIndex(s_map.get(self.ws.status, 0))

    def _save(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, '提示', '请填写工位名称')
            return
        self.result = {
            'name': name, 'type': self.cb_type.currentText(),
            'capacity': self.sp_cap.value(),
            'equipment': self.te_equip.toPlainText().strip(),
            'status': self.cb_status.currentText().split()[0]
        }
        self.accept()


class WorkstationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()
        self.setStyleSheet(_line_style())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)

        h = QLabel('🛁 工位资源建档与负载')
        h.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(h)

        tb = QHBoxLayout()
        tb.setSpacing(12)
        self.cb_filter_type = QComboBox()
        self.cb_filter_type.addItem('全部类型', None)
        for t in WorkstationFormDialog.TYPES:
            self.cb_filter_type.addItem(t, t)
        self.cb_filter_type.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_filter_type)
        self.cb_filter_status = QComboBox()
        self.cb_filter_status.addItem('全部状态', None)
        self.cb_filter_status.addItem('启用', 'active')
        self.cb_filter_status.addItem('维护', 'maintenance')
        self.cb_filter_status.addItem('停用', 'offline')
        self.cb_filter_status.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_filter_status)
        tb.addStretch(1)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 搜索工位名/设备...')
        self.ed_search.returnPressed.connect(self.refresh)
        tb.addWidget(self.ed_search)
        btn_add = QPushButton('➕ 新建工位')
        btn_add.setStyleSheet(_btn_primary())
        btn_add.clicked.connect(self._on_add)
        tb.addWidget(btn_add)
        root.addLayout(tb)

        self.table = QTableWidget()
        self.table.setStyleSheet('''
            QTableWidget { background:#fff; border-radius:8px; border:1px solid #e5e7eb; gridline-color:#f3f4f6; }
            QTableWidget::item { padding: 6px 10px; }
            QHeaderView::section { background:#f9fafb; padding:10px; border:none; border-bottom:2px solid #e5e7eb; color:#374151; font-weight:bold; }
        ''')
        headers = ['ID', '工位名', '类型', '容量', '设备配置', '状态', '7日负载评分', '负载状态', '操作']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self.lbl = QLabel('共 0 个工位')
        self.lbl.setStyleSheet('color:#6b7280; font-size:12px;')
        root.addWidget(self.lbl)

    def refresh(self):
        t = self.cb_filter_type.currentData()
        s = self.cb_filter_status.currentData()
        kw = self.ed_search.text().strip()
        all_ws = Scheduling.list_workstations(status=s, ws_type=t)
        if kw:
            all_ws = [w for w in all_ws if kw in (w.name or '') or kw in (w.equipment or '')]
        self.table.setRowCount(len(all_ws))
        status_map = {'active': ('🟢 启用', '#10b981'), 'maintenance': ('🟡 维护', '#f59e0b'), 'offline': ('🔴 停用', '#ef4444')}
        for row, w in enumerate(all_ws):
            sts, sc = status_map.get(w.status, (w.status, '#6b7280'))
            load = w.load_score or 0.0
            vals = [str(w.id), w.name, w.type, f'{w.capacity} 只', w.equipment or '-', sts, f'{load:.2f}']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 5:
                    it.setForeground(Qt.GlobalColor.darkGreen if w.status == 'active' else Qt.GlobalColor.red)
                self.table.setItem(row, c, it)

            pbar = QProgressBar()
            pbar.setRange(0, 10)
            pbar.setValue(min(int(load), 10))
            pbar.setTextVisible(True)
            pbar.setFormat('%v/10')
            pbar.setFixedHeight(22)
            if load < 4:
                pbar.setStyleSheet('QProgressBar{border:1px solid #d1d5db;border-radius:4px;text-align:center;background:#fff;}QProgressBar::chunk{background:#10b981;border-radius:3px;}')
                load_txt = '空闲'
            elif load < 7.5:
                pbar.setStyleSheet('QProgressBar{border:1px solid #d1d5db;border-radius:4px;text-align:center;background:#fff;}QProgressBar::chunk{background:#f59e0b;border-radius:3px;}')
                load_txt = '适中'
            else:
                pbar.setStyleSheet('QProgressBar{border:1px solid #d1d5db;border-radius:4px;text-align:center;background:#fff;}QProgressBar::chunk{background:#ef4444;border-radius:3px;}')
                load_txt = '繁忙'
            load_container = QFrame()
            ll = QHBoxLayout(load_container)
            ll.setContentsMargins(8, 4, 8, 4)
            ll.setSpacing(8)
            ll.addWidget(pbar, 1)
            lbl_t = QLabel(load_txt)
            lbl_t.setStyleSheet('font-size:12px;color:#374151;')
            ll.addWidget(lbl_t)
            self.table.setCellWidget(row, 7, load_container)

            opf = QFrame()
            ol = QHBoxLayout(opf)
            ol.setContentsMargins(6, 3, 6, 3)
            ol.setSpacing(6)
            be = QPushButton('编辑')
            be.setStyleSheet(_btn_secondary())
            be.clicked.connect(lambda _, _w=w: self._on_edit(_w))
            bd = QPushButton('删除')
            bd.setStyleSheet(_btn_danger())
            bd.clicked.connect(lambda _, _w=w: self._on_del(_w))
            ol.addStretch(1)
            ol.addWidget(be)
            ol.addWidget(bd)
            self.table.setCellWidget(row, 8, opf)
            self.table.setRowHeight(row, 46)
        self.lbl.setText(f'共 {len(all_ws)} 个工位')

    def _on_add(self):
        d = WorkstationFormDialog(self)
        if d.exec():
            Scheduling.add_workstation(**d.result)
            self.refresh()

    def _on_edit(self, w):
        d = WorkstationFormDialog(self, w)
        if d.exec():
            Scheduling.update_workstation(w.id, **d.result)
            self.refresh()

    def _on_del(self, w):
        r = QMessageBox.question(self, '确认删除', f'确定删除工位「{w.name}」？',
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            Scheduling.delete_workstation(w.id)
            self.refresh()
