from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QDateEdit, QScrollArea, QFrame, QGridLayout, QSizePolicy,
                             QComboBox, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from models import Appointment
from modules import Scheduling


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:8px 18px;
            border-radius:6px; font-weight:bold; border:none; }
            QPushButton:hover { background:#f59e0b; }'''
def _btn_secondary():
    return '''QPushButton { background:#e5e7eb; color:#374151; padding:8px 16px;
            border-radius:6px; border:none; }
            QPushButton:hover { background:#d1d5db; }'''
def _line_style():
    return '''QDateEdit, QComboBox {
        padding: 7px 10px; border:1px solid #d1d5db; border-radius:5px;
        background:#fff; font-size:13px; }'''


STATUS_COLOR = {
    'pending': '#fef3c7',
    'confirmed': '#dbeafe',
    'completed': '#d1fae5',
    'cancelled': '#e5e7eb'
}
STATUS_BORDER = {
    'pending': '#f59e0b',
    'confirmed': '#3b82f6',
    'completed': '#10b981',
    'cancelled': '#9ca3af'
}


class TimeBar(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, row, col, hour, minute, free=True, appt_info=None, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.hour = hour
        self.minute = minute
        self.free = free
        self.appt_info = appt_info
        self._build()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _build(self):
        self.setMinimumSize(60, 44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        if self.appt_info:
            st = self.appt_info.get('status', 'confirmed')
            self.setStyleSheet(f'''
                QWidget {{
                    background: {STATUS_COLOR.get(st, '#dbeafe')};
                    border-left: 3px solid {STATUS_BORDER.get(st, '#3b82f6')};
                    border-radius: 4px;
                    margin: 1px;
                }}
            ''')
            lbl = QLabel(f"{self.appt_info.get('pet_name', '?')}\n{self.appt_info.get('service_name', '')[:6]}")
            lbl.setStyleSheet(f'color:#1f2937; font-size:11px; padding:2px 4px;')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
        else:
            color = '#f0fdf4' if self.free else '#fef2f2'
            border = '#86efac' if self.free else '#fca5a5'
            self.setStyleSheet(f'''
                QWidget {{
                    background: {color};
                    border: 1px dashed {border};
                    border-radius: 3px;
                    margin: 1px;
                }}
            ''')
            text = f'{self.hour:02d}:{self.minute:02d}' if self.minute % 30 == 0 else ''
            lbl = QLabel(text)
            lbl.setStyleSheet('color:#6b7280; font-size:10px;')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)

    def mousePressEvent(self, ev):
        self.clicked.emit(self.row)
        super().mousePressEvent(ev)


class SchedulePage(QWidget):
    SLOT_MIN = 30

    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()
        self.setStyleSheet(_line_style())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        h = QLabel('🗓 排期看板 · 工位占用一览')
        h.setStyleSheet('font-size:24px; font-weight:bold; color:#111827;')
        root.addWidget(h)

        legend = QFrame()
        legend.setStyleSheet('background:#fff; border-radius:8px; padding:4px;')
        lg = QHBoxLayout(legend)
        lg.setContentsMargins(14, 10, 14, 10)
        lg.setSpacing(18)
        def leg(color, border, text):
            r = QFrame()
            r.setFixedSize(22, 22)
            r.setStyleSheet(f'background:{color};border-left:3px solid {border};border-radius:3px;')
            ll = QHBoxLayout()
            ll.setContentsMargins(0,0,0,0)
            ll.addWidget(r)
            ll.addWidget(QLabel(text))
            wrap = QFrame()
            wrap.setLayout(ll)
            return wrap
        lg.addWidget(leg(STATUS_COLOR['confirmed'], STATUS_BORDER['confirmed'], '已确认'))
        lg.addWidget(leg(STATUS_COLOR['pending'], STATUS_BORDER['pending'], '待确认'))
        lg.addWidget(leg(STATUS_COLOR['completed'], STATUS_BORDER['completed'], '已完成'))
        lg.addWidget(leg(STATUS_COLOR['cancelled'], STATUS_BORDER['cancelled'], '已取消'))
        lg.addWidget(leg('#f0fdf4', '#86efac', '空闲可用'))
        lg.addStretch(1)
        root.addWidget(legend)

        tb = QHBoxLayout()
        tb.setSpacing(12)
        btn_prev = QPushButton('◀ 前日')
        btn_prev.setStyleSheet(_btn_secondary())
        btn_prev.clicked.connect(lambda: self._shift_day(-1))
        tb.addWidget(btn_prev)
        self.de_date = QDateEdit()
        self.de_date.setCalendarPopup(True)
        self.de_date.setDate(QDate.currentDate())
        self.de_date.setDisplayFormat('yyyy-MM-dd (dddd)')
        self.de_date.dateChanged.connect(self.refresh)
        tb.addWidget(self.de_date)
        btn_next = QPushButton('次日 ▶')
        btn_next.setStyleSheet(_btn_secondary())
        btn_next.clicked.connect(lambda: self._shift_day(1))
        tb.addWidget(btn_next)
        btn_today = QPushButton('今天')
        btn_today.setStyleSheet(_btn_primary())
        btn_today.clicked.connect(lambda: (self.de_date.setDate(QDate.currentDate()), self.refresh()))
        tb.addWidget(btn_today)
        tb.addStretch(1)
        self.lbl_summary = QLabel('')
        self.lbl_summary.setStyleSheet('color:#374151; font-size:13px;')
        tb.addWidget(self.lbl_summary)
        root.addLayout(tb)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('QScrollArea{background:#fff;border-radius:8px;border:1px solid #e5e7eb;}')
        self.grid_host = QWidget()
        self.scroll.setWidget(self.grid_host)
        root.addWidget(self.scroll, 1)

    def _shift_day(self, delta):
        nd = self.de_date.date().addDays(delta)
        self.de_date.setDate(nd)
        self.refresh()

    def refresh(self):
        date_str = self.de_date.date().toString('yyyy-MM-dd')
        d = self.de_date.date()
        self.de_date.setDisplayFormat(f'yyyy-MM-dd (周{"日一二三四五六"[d.dayOfWeek()%7]})')

        while self.scroll.widget():
            w = self.scroll.takeWidget()
            w.setParent(None)

        self.grid_host = QWidget()
        self.scroll.setWidget(self.grid_host)
        grid = QGridLayout(self.grid_host)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(2)

        ws_list = Scheduling.list_workstations()
        start_h, end_h = Scheduling.WORK_START_HOUR, Scheduling.WORK_END_HOUR
        slots_per_h = 60 // self.SLOT_MIN
        total_slots = (end_h - start_h) * slots_per_h

        header_lbl = QLabel('时间 / 工位')
        header_lbl.setStyleSheet('background:#f9fafb; padding:10px; font-weight:bold; color:#374151; border-bottom:2px solid #e5e7eb; border-radius:4px;')
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_lbl.setMinimumHeight(44)
        grid.addWidget(header_lbl, 0, 0)

        for col, ws in enumerate(ws_list):
            hf = QFrame()
            hf.setStyleSheet('background:#f9fafb; border-bottom:2px solid #e5e7eb; border-radius:4px;')
            hl = QVBoxLayout(hf)
            hl.setContentsMargins(8, 6, 8, 6)
            hl.setSpacing(2)
            name = QLabel(ws.name)
            name.setStyleSheet('font-weight:bold; color:#1f2937; font-size:13px;')
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tp = QLabel(f'{ws.type} · 负载{ws.load_score:.1f}')
            tp.setStyleSheet('color:#6b7280; font-size:11px;')
            tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.addWidget(name)
            hl.addWidget(tp)
            hf.setMinimumHeight(52)
            grid.addWidget(hf, 0, col + 1)

        appts_by_ws = {}
        for ws in ws_list:
            occ = Scheduling.get_workstation_occupied_ranges(ws.id, date_str)
            appts_by_ws[ws.id] = []
            for s, e, aid in occ:
                a = Appointment.get(aid)
                info = {'start': s, 'end': e, 'status': a.status if a else 'confirmed'}
                from models import Pet, Service
                if a:
                    p = Pet.get(a.pet_id)
                    sv = Service.get(a.service_id)
                    if p: info['pet_name'] = p.name
                    if sv: info['service_name'] = sv.name
                appts_by_ws[ws.id].append(info)

        for i in range(total_slots):
            abs_min = i * self.SLOT_MIN
            h = start_h + abs_min // 60
            m = abs_min % 60
            t_label = QLabel(f'{h:02d}:{m:02d}')
            t_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_label.setStyleSheet(f'''
                QLabel {{
                    background: {'#fefce8' if m == 0 else '#fff'};
                    padding: 8px 4px;
                    color: #374151;
                    font-weight: {'bold' if m == 0 else 'normal'};
                    font-size: 12px;
                    border-right: 1px solid #f3f4f6;
                    border-radius: 3px;
                }}
            ''')
            t_label.setMinimumHeight(44)
            grid.addWidget(t_label, i + 1, 0)

            for col, ws in enumerate(ws_list):
                slot_dt = datetime.strptime(f'{date_str} {h:02d}:{m:02d}', '%Y-%m-%d %H:%M')
                slot_end_dt = slot_dt + timedelta(minutes=self.SLOT_MIN)
                occupied_info = None
                for info in appts_by_ws.get(ws.id, []):
                    try:
                        a_s = datetime.strptime(info['start'], '%Y-%m-%d %H:%M')
                        a_e = datetime.strptime(info['end'], '%Y-%m-%d %H:%M')
                        if a_s <= slot_dt and slot_dt < a_e:
                            occupied_info = info
                            break
                    except:
                        pass
                bar = TimeBar(i + 1, col + 1, h, m, free=(occupied_info is None), appt_info=occupied_info)
                grid.addWidget(bar, i + 1, col + 1)

        total_occ, total_slots_count = 0, total_slots * len(ws_list)
        for ws in ws_list:
            for info in appts_by_ws.get(ws.id, []):
                try:
                    a_s = datetime.strptime(info['start'], '%Y-%m-%d %H:%M')
                    a_e = datetime.strptime(info['end'], '%Y-%m-%d %H:%M')
                    total_occ += int((a_e - a_s).total_seconds() / 60 / self.SLOT_MIN)
                except:
                    pass
        rate = (total_occ / total_slots_count * 100) if total_slots_count else 0
        self.lbl_summary.setText(
            f'工位数: {len(ws_list)}  |  排期占用: {total_occ}/{total_slots_count} 格  |  占用率: {rate:.1f}%'
        )
