import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFrame, QFileDialog)
from PyQt6.QtCore import Qt
from modules import BackupManager
from models import Database


def _btn_primary():
    return '''QPushButton { background:#fbbf24; color:#1f2937; padding:10px 24px;
             border-radius:6px; font-weight:bold; font-size:14px; }
             QPushButton:hover { background:#f59e0b; }'''

def _btn_danger():
    return '''QPushButton { background:#ef4444; color:#fff; padding:10px 20px;
             border-radius:6px; font-weight:bold; font-size:14px; }
             QPushButton:hover { background:#dc2626; }'''

def _btn_secondary():
    return '''QPushButton { background:#6b7280; color:#fff; padding:10px 20px;
             border-radius:6px; font-size:14px; } QPushButton:hover { background:#4b5563; }'''


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        title = QLabel('⚙️ 系统设置')
        title.setStyleSheet('font-size:24px; font-weight:bold; color:#111827; padding:8px 0;')
        root.addWidget(title)

        backup_card = QFrame()
        backup_card.setStyleSheet('''
            QFrame { background:#fff; border-radius:12px; }
        ''')
        bk_lay = QVBoxLayout(backup_card)
        bk_lay.setContentsMargins(24, 20, 24, 20)
        bk_lay.setSpacing(14)

        bk_title = QHBoxLayout()
        t = QLabel('💾 数据备份与恢复')
        t.setStyleSheet('font-size:18px; font-weight:bold; color:#111827;')
        bk_title.addWidget(t)
        bk_title.addStretch(1)
        self.btn_backup = QPushButton('📷 立即备份')
        self.btn_backup.setStyleSheet(_btn_primary())
        self.btn_backup.clicked.connect(self._on_backup)
        bk_title.addWidget(self.btn_backup)
        bk_lay.addLayout(bk_title)

        desc = QLabel('定期备份门店数据，可选择备份文件恢复。恢复前会自动备份当前数据。')
        desc.setStyleSheet('color:#6b7280; font-size:13px; padding-bottom:8px;')
        bk_lay.addWidget(desc)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(['备份时间', '文件名', '大小', '操作'])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setStyleSheet('''
            QTableWidget { gridline-color:#f3f4f6; border:none; font-size:13px; }
            QHeaderView::section { background:#f9fafb; padding:12px; font-weight:bold; border:none; border-bottom:2px solid #e5e7eb; }
            QTableWidget::item { padding:10px; }
        ''')
        bk_lay.addWidget(self.tbl, 1)

        root.addWidget(backup_card, 1)

        danger_card = QFrame()
        danger_card.setStyleSheet('QFrame{background:#fff; border-radius:12px;}')
        d_lay = QVBoxLayout(danger_card)
        d_lay.setContentsMargins(24, 20, 24, 20)
        d_title = QLabel('⚠️ 数据库版本')
        d_title.setStyleSheet('font-size:16px; font-weight:bold; color:#111827;')
        d_lay.addWidget(d_title)
        self.lbl_version = QLabel()
        self.lbl_version.setStyleSheet('color:#374151; font-size:13px; padding:8px 0;')
        d_lay.addWidget(self.lbl_version)
        root.addWidget(danger_card)

    def refresh(self):
        backups = BackupManager.list_backups()
        self.tbl.setRowCount(0)
        for bk in backups:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(bk['created_at']))
            self.tbl.setItem(r, 1, QTableWidgetItem(bk['filename']))
            size_text = f'{bk["size_kb"]} KB' if bk['size_kb'] < 1024 else f'{bk["size_kb"]/1024:.1f} MB'
            self.tbl.setItem(r, 2, QTableWidgetItem(size_text))
            op_w = QWidget()
            op_lay = QHBoxLayout(op_w)
            op_lay.setContentsMargins(4, 4, 4, 4)
            op_lay.setSpacing(8)
            btn_restore = QPushButton('恢复')
            btn_restore.setStyleSheet(_btn_danger())
            btn_restore.setFixedWidth(80)
            btn_restore.clicked.connect(lambda _, f=bk['filename']: self._on_restore(f))
            op_lay.addStretch(1)
            op_lay.addWidget(btn_restore)
            self.tbl.setCellWidget(r, 3, op_w)

        db = Database()
        cur = db.conn().cursor()
        cur.execute("PRAGMA user_version")
        v = cur.fetchone()[0]
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'petshop.db')
        size = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0
        self.lbl_version.setText(f'当前数据库版本: v{v} | 数据文件大小: {size} KB | 备份目录: {BackupManager.backup_dir()}')

    def _on_backup(self):
        result, err = BackupManager.create_backup()
        if err:
            QMessageBox.warning(self, '备份失败', err)
            return
        QMessageBox.information(self, '备份成功',
                                f'已创建备份文件:\n{result["filename"]}\n大小: {result["size_kb"]} KB')
        self.refresh()

    def _on_restore(self, filename):
        backups = BackupManager.list_backups()
        info = next((b for b in backups if b['filename'] == filename), None)
        if not info:
            QMessageBox.warning(self, '错误', '备份文件不存在')
            return
        r = QMessageBox.question(
            self, '⚠️ 确认恢复',
            f'确定要将数据库恢复到以下备份吗？\n\n'
            f'  备份时间: {info["created_at"]}\n'
            f'  文件大小: {info["size_kb"]} KB\n'
            f'  文件名: {filename}\n\n'
            f'⚠️ 重要提示:\n'
            f'  • 恢复前会自动备份当前数据到 backups 目录\n'
            f'  • 恢复完成后需要重新启动程序\n'
            f'  • 当前所有未备份数据将被覆盖',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        r2 = QMessageBox.question(self, '最终确认',
                                  '真的要执行恢复操作吗？此操作无法撤销！',
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                  QMessageBox.StandardButton.No)
        if r2 != QMessageBox.StandardButton.Yes:
            return
        ok, msg = BackupManager.restore_backup(filename)
        if ok:
            QMessageBox.information(self, '恢复成功',
                                    f'{msg}\n\n请关闭程序并重新打开。')
        else:
            QMessageBox.warning(self, '恢复失败', msg)
