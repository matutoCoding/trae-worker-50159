from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QFormLayout, QComboBox, QDateEdit, QTimeEdit,
                             QTextEdit, QMessageBox, QFrame, QGroupBox, QRadioButton,
                             QListWidget, QListWidgetItem, QDoubleSpinBox, QSpinBox,
                             QGridLayout)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QColor, QBrush

from models import Pet, Service, Appointment, Workstation
from modules import Scheduling, AllocationEngine, PricingEngine


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
def _btn_danger():
    return '''QPushButton { background:#fee2e2; color:#b91c1c; padding:6px 14px;
            border-radius:5px; border:none; }
            QPushButton:hover { background:#fecaca; }'''
def _line_style():
    return '''QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox, QSpinBox, QTextEdit {
        padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
        background:#fff; font-size:13px; }
        QLineEdit:focus, QComboBox:focus { border:1px solid #fbbf24; }'''


class AppointmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('📅 创建美容预约 - 智能分配工位')
        self.resize(720, 620)
        self._best_alloc = None
        self._all_candidates = []
        self._build()
        self._reload_pets_services()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        tip = QLabel('💡 宠主只需选择时间和项目，系统自动从空闲工位中择优分配（避免碎片、负载均衡）')
        tip.setStyleSheet('background:#fef3c7; color:#92400e; padding:10px 14px; border-radius:8px; font-size:13px;')
        tip.setWordWrap(True)
        root.addWidget(tip)

        form_box = QGroupBox('预约信息')
        form_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        form = QFormLayout(form_box)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_pet = QComboBox()
        form.addRow('选择宠物*:', self.cb_pet)

        self.cb_service = QComboBox()
        self.cb_service.currentIndexChanged.connect(self._on_service_changed)
        form.addRow('服务项目*:', self.cb_service)

        self.lbl_dur = QLabel('— 分钟')
        self.lbl_dur.setStyleSheet('color:#6b7280;')
        form.addRow('项目时长:', self.lbl_dur)

        self.de_date = QDateEdit()
        self.de_date.setCalendarPopup(True)
        self.de_date.setDate(QDate.currentDate())
        self.de_date.setDisplayFormat('yyyy-MM-dd')
        form.addRow('预约日期*:', self.de_date)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(8)
        self.te_start = QTimeEdit()
        self.te_start.setTime(QTime(10, 0))
        self.te_start.setDisplayFormat('HH:mm')
        self.te_start.setMinimumTime(QTime(9, 0))
        self.te_start.setMaximumTime(QTime(20, 0))
        time_layout.addWidget(self.te_start)
        time_layout.addWidget(QLabel('~'))
        self.lbl_end = QLabel('—:—')
        self.lbl_end.setStyleSheet('color:#374151; padding: 6px; background:#f9fafb; border-radius:4px; min-width:80px;')
        time_layout.addWidget(self.lbl_end)
        time_layout.addStretch(1)
        time_wrap = QFrame()
        time_wrap.setLayout(time_layout)
        form.addRow('预约时间*:', time_wrap)

        self.cb_type = QComboBox()
        self.cb_type.addItem('不限类型（自动匹配）', None)
        self.cb_type.addItem('标准美容', '标准美容')
        self.cb_type.addItem('SPA护理', 'SPA护理')
        self.cb_type.addItem('特殊美容', '特殊美容')
        form.addRow('偏好工位:', self.cb_type)

        self.te_notes = QTextEdit()
        self.te_notes.setFixedHeight(60)
        self.te_notes.setPlaceholderText('备注：宠物特性、特殊要求...')
        form.addRow('备注:', self.te_notes)
        root.addWidget(form_box)

        self.btn_check = QPushButton('🔍 查询可用工位并自动推荐')
        self.btn_check.setStyleSheet(_btn_green())
        self.btn_check.clicked.connect(self._check_allocation)
        root.addWidget(self.btn_check)

        cand_box = QGroupBox('工位分配推荐（按综合评分排序）')
        cand_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        cl = QVBoxLayout(cand_box)
        cl.setContentsMargins(12, 14, 12, 12)
        self.list_cand = QListWidget()
        self.list_cand.setStyleSheet('''
            QListWidget { background:#fff; border:1px solid #e5e7eb; border-radius:6px; }
            QListWidget::item { padding: 10px; border-bottom:1px solid #f3f4f6; }
            QListWidget::item:selected { background:#fef3c7; color:#1f2937; }
        ''')
        self.list_cand.currentItemChanged.connect(self._on_cand_changed)
        cl.addWidget(self.list_cand)
        root.addWidget(cand_box, 1)

        price_box = QGroupBox('费用预估')
        price_box.setStyleSheet('QGroupBox{font-weight:bold;color:#374151;border:1px solid #e5e7eb;border-radius:8px;margin-top:12px;padding-top:14px;}QGroupBox::title{subcontrol-origin:margin;left:14px;padding:0 6px;}')
        pl = QFormLayout(price_box)
        pl.setSpacing(8)
        self.lbl_price_base = QLabel('—')
        self.lbl_price_cap = QLabel('—')
        self.lbl_price_final = QLabel('—')
        self.lbl_price_final.setStyleSheet('font-size:18px; font-weight:bold; color:#10b981;')
        self.lbl_price_note = QLabel('')
        self.lbl_price_note.setStyleSheet('color:#f59e0b; font-size:12px;')
        pl.addRow('起步价:', self.lbl_price_base)
        pl.addRow('封顶价:', self.lbl_price_cap)
        pl.addRow('预估应付:', self.lbl_price_final)
        pl.addRow('', self.lbl_price_note)
        root.addWidget(price_box)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)
        b1 = QPushButton('取消')
        b1.setStyleSheet(_btn_secondary())
        b1.clicked.connect(self.reject)
        btns.addWidget(b1)
        b2 = QPushButton('✅ 确认预约并分配工位')
        b2.setStyleSheet(_btn_primary())
        b2.clicked.connect(self._confirm)
        btns.addWidget(b2)
        root.addLayout(btns)

        self._on_service_changed()

    def _reload_pets_services(self):
        pets = Pet.list()
        self.cb_pet.clear()
        for p in pets:
            self.cb_pet.addItem(f'{p.name} - {p.species}/{p.breed or "?"} (主人:{p.owner_name})', p.id)
        services = Service.list()
        self.cb_service.clear()
        for s in services:
            tag = '📦套餐' if s.is_package else '🧴标准'
            self.cb_service.addItem(f'{tag} {s.name} ({s.duration}分钟 ¥{s.base_price:.0f}~¥{s.cap_price:.0f})', s.id)

    def _on_service_changed(self):
        sid = self.cb_service.currentData()
        if sid:
            svc = Service.get(sid)
            if svc:
                self.lbl_dur.setText(f'{svc.duration} 分钟')
                start_t = self.te_start.time()
                end_t = start_t.addSecs(svc.duration * 60)
                self.lbl_end.setText(end_t.toString('HH:mm'))
        self._update_price_preview()

    def _update_price_preview(self):
        sid = self.cb_service.currentData()
        pid = self.cb_pet.currentData()
        if not sid:
            return
        info, err = PricingEngine.calculate_price(sid, pid)
        if info:
            self.lbl_price_base.setText(f'¥{info["base_price"]:.2f}')
            self.lbl_price_cap.setText(f'¥{info["cap_price"]:.2f}')
            self.lbl_price_final.setText(f'¥{info["final_amount"]:.2f}')
            notes = []
            if info.get('is_package'):
                notes.append('📦 套餐按一口价计费')
            if info.get('weight_surcharge', 0) > 0:
                notes.append(f'大型犬加价 ¥{info["weight_surcharge"]:.2f}')
            if info.get('species_surcharge', 0) > 0:
                notes.append(f'猫只护理加价 ¥{info["species_surcharge"]:.2f}')
            notes.extend(info.get('bound_warnings', []))
            self.lbl_price_note.setText(' | '.join(notes))

    def _check_allocation(self):
        sid = self.cb_service.currentData()
        pid = self.cb_pet.currentData()
        if not sid or not pid:
            QMessageBox.warning(self, '提示', '请先选择宠物和服务项目')
            return
        svc = Service.get(sid)
        date_str = self.de_date.date().toString('yyyy-MM-dd')
        start_str = self.te_start.time().toString('HH:mm')
        ws_type = self.cb_type.currentData()
        alloc, all_cand = AllocationEngine.allocate_best_fit(
            date_str, start_str, svc.duration, ws_type
        )
        self._best_alloc = alloc
        self._all_candidates = all_cand
        self.list_cand.clear()
        if not all_cand:
            it = QListWidgetItem('⚠️  所选时间无可分配工位，请尝试其他时间或放宽工位类型')
            it.setForeground(QColor('#b91c1c'))
            self.list_cand.addItem(it)
            return
        for i, c in enumerate(all_cand[:15]):
            ws = c['workstation']
            badge = '⭐ 推荐' if i == 0 else f'  备选{i}'
            txt = (f'{badge}  工位: {ws["name"]} ({ws["type"]})  |  时段: {c["start"].split()[1]} - {c["end"].split()[1]}\n'
                   f'      评分: 综合{c["total_score"]:.1f} (碎片{c["fragment_score"]:.1f} + 负载{c["load_score"]:.1f})\n'
                   f'      空闲衔接: 前{c["free_before_min"]}分钟 / 后{c["free_after_min"]}分钟')
            item = QListWidgetItem(txt)
            item.setData(Qt.ItemDataRole.UserRole, c)
            if i == 0:
                item.setForeground(QColor('#059669'))
            self.list_cand.addItem(item)
        self.list_cand.setCurrentRow(0)
        self._update_price_preview()

    def _on_cand_changed(self, cur, prev):
        if cur:
            cand = cur.data(Qt.ItemDataRole.UserRole)
            self._best_alloc = cand

    def _confirm(self):
        if not self._best_alloc:
            QMessageBox.warning(self, '提示', '请先点击「查询可用工位」获取分配推荐')
            return
        pid = self.cb_pet.currentData()
        sid = self.cb_service.currentData()
        alloc = self._best_alloc
        appt_id = Appointment.add({
            'pet_id': pid,
            'workstation_id': alloc['workstation']['id'],
            'service_id': sid,
            'start_time': alloc['start'],
            'end_time': alloc['end'],
            'status': Appointment.STATUS_CONFIRMED,
            'alloc_score': alloc['total_score'],
            'notes': self.te_notes.toPlainText().strip()
        })
        AllocationEngine._recalc_workstation_load(alloc['workstation']['id'])
        QMessageBox.information(
            self, '预约成功',
            f'✅ 已成功创建预约\n\n'
            f'预约号: #{appt_id}\n'
            f'分配工位: {alloc["workstation"]["name"]}\n'
            f'时段: {alloc["start"]} ~ {alloc["end"]}\n'
            f'分配评分: {alloc["total_score"]:.1f}'
        )
        self.accept()


class AppointmentPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()
        self.setStyleSheet(_line_style())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(20)
        h = QLabel('📅 美容预约管理 · 智能工位分配')
        h.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(h)

        tb = QHBoxLayout()
        tb.setSpacing(12)
        self.de_date = QDateEdit()
        self.de_date.setCalendarPopup(True)
        self.de_date.setDate(QDate.currentDate())
        self.de_date.setDisplayFormat('yyyy-MM-dd')
        self.de_date.dateChanged.connect(lambda: self.refresh())
        tb.addWidget(QLabel('查看日期:'))
        tb.addWidget(self.de_date)
        self.cb_status = QComboBox()
        self.cb_status.addItem('全部状态', None)
        for s, t in [('confirmed', '✅ 已确认'), ('pending', '⏳ 待确认'), ('completed', '✂️ 已完成'), ('cancelled', '❌ 已取消')]:
            self.cb_status.addItem(t, s)
        self.cb_status.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self.cb_status)
        tb.addStretch(1)
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('🔍 搜索宠物/主人/工位/项目...')
        self.ed_search.returnPressed.connect(self.refresh)
        tb.addWidget(self.ed_search)
        btn_ref = QPushButton('🔄 刷新')
        btn_ref.setStyleSheet(_btn_secondary())
        btn_ref.clicked.connect(self.refresh)
        tb.addWidget(btn_ref)
        btn_add = QPushButton('➕ 新建预约（自动分配）')
        btn_add.setStyleSheet(_btn_primary())
        btn_add.clicked.connect(self._on_new)
        tb.addWidget(btn_add)
        root.addLayout(tb)

        self.table = QTableWidget()
        self.table.setStyleSheet('''
            QTableWidget { background:#fff; border-radius:8px; border:1px solid #e5e7eb; gridline-color:#f3f4f6; }
            QTableWidget::item { padding: 6px 10px; }
            QHeaderView::section { background:#f9fafb; padding:10px; border:none; border-bottom:2px solid #e5e7eb; color:#374151; font-weight:bold; }
        ''')
        hd = ['ID', '时段', '宠物', '主人', '电话', '项目', '分配工位', '状态', '评分', '操作']
        self.table.setColumnCount(len(hd))
        self.table.setHorizontalHeaderLabels(hd)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.lbl = QLabel('共 0 条预约')
        self.lbl.setStyleSheet('color:#6b7280; font-size:12px;')
        root.addWidget(self.lbl)

    def refresh(self):
        d = self.de_date.date().toString('yyyy-MM-dd')
        s = self.cb_status.currentData()
        kw = self.ed_search.text().strip()
        if kw:
            rows = Appointment.list(kw)
            rows = [r for r in rows if r['start_time'].split()[0] == d or not d]
            if s:
                rows = [r for r in rows if r['status'] == s]
        else:
            rows = Appointment.list_by_date(d, s)
        self.table.setRowCount(len(rows))
        st_map = {
            'pending': ('⏳待确认', '#f59e0b'),
            'confirmed': ('✅已确认', '#3b82f6'),
            'completed': ('✂️已完成', '#10b981'),
            'cancelled': ('❌已取消', '#6b7280')
        }
        for row, r in enumerate(rows):
            start = r['start_time'].split()[1] if ' ' in r['start_time'] else r['start_time']
            end = r['end_time'].split()[1] if ' ' in r['end_time'] else r['end_time']
            pet_info = f"{r.get('pet_name','?')} ({r.get('pet_species','')}/{r.get('pet_breed','')})"
            vals = [
                str(r['id']), f'{start} ~ {end}',
                pet_info, r.get('owner_name', ''), r.get('owner_phone', ''),
                f"{r.get('service_name','')} ({r.get('duration','')}分)",
                r.get('ws_name', '-'),
                st_map.get(r['status'], (r['status'], '#000'))[0],
                f"{r.get('alloc_score',0):.1f}"
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 7:
                    it.setForeground(QBrush(QColor(st_map.get(r['status'], ('', '#000'))[1])))
                if c == 1:
                    it.setFont(self.table.font())
                self.table.setItem(row, c, it)

            opf = QFrame()
            ol = QHBoxLayout(opf)
            ol.setContentsMargins(4, 3, 4, 3)
            ol.setSpacing(4)
            if r['status'] == 'confirmed':
                br = QPushButton('重分配')
                br.setStyleSheet(_btn_secondary())
                br.clicked.connect(lambda _, _id=r['id']: self._on_realloc(_id))
                ol.addWidget(br)
                bc = QPushButton('完成')
                bc.setStyleSheet(_btn_green())
                bc.clicked.connect(lambda _, _id=r['id']: self._on_complete(_id))
                ol.addWidget(bc)
            if r['status'] not in ('cancelled', 'completed'):
                bx = QPushButton('取消')
                bx.setStyleSheet(_btn_danger())
                bx.clicked.connect(lambda _, _id=r['id']: self._on_cancel(_id))
                ol.addWidget(bx)
            self.table.setCellWidget(row, 9, opf)
            self.table.setRowHeight(row, 42)
        self.lbl.setText(f'{d} 共 {len(rows)} 条预约')

    def _on_new(self):
        d = AppointmentDialog(self)
        if d.exec():
            self.refresh()

    def _on_realloc(self, appt_id):
        r, info = AllocationEngine.reallocate_appointment(appt_id)
        if r:
            QMessageBox.information(self, '重分配成功',
                                    f'新工位: {info["workstation"]["name"]}\n时段: {info["start"]} ~ {info["end"]}')
            self.refresh()
        else:
            QMessageBox.warning(self, '重分配失败', info or '无可用工位')

    def _on_complete(self, appt_id):
        Scheduling.update_appointment_status(appt_id, Appointment.STATUS_COMPLETED)
        self.refresh()

    def _on_cancel(self, appt_id):
        r = QMessageBox.question(self, '确认', '确定取消此预约？',
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            AllocationEngine.cancel_appointment(appt_id)
            self.refresh()
