"""Sidebar — department list + DM list with unread badges."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)
import qtawesome as qta
from client.gui.theme import get_colors


class Sidebar(QWidget):
    department_selected = Signal(int, str)
    dm_selected = Signal(int, str)
    settings_clicked = Signal()
    admin_clicked = Signal()
    logout_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self._unread = {"dept": {}, "dm": {}}
        self._build_ui()

    def _build_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 12, 8, 8)
        self.setStyleSheet(f"background-color: {c['bg_secondary']};")

        layout.addWidget(self._make_label("💬 Departments", c))
        self.dept_list = QListWidget()
        self.dept_list.currentItemChanged.connect(self._on_dept)
        layout.addWidget(self.dept_list, 3)

        layout.addWidget(self._make_label("📩 Direct Messages", c))
        self.dm_list = QListWidget()
        self.dm_list.currentItemChanged.connect(self._on_dm)
        layout.addWidget(self.dm_list, 2)

        btn_row = QHBoxLayout()
        
        self.admin_btn = QPushButton(" Admin")
        self.admin_btn.setIcon(qta.icon('fa5s.shield-alt', color=c['text_primary']))
        self.admin_btn.setVisible(False)
        self.admin_btn.clicked.connect(self.admin_clicked.emit)
        btn_row.addWidget(self.admin_btn)
        
        settings_btn = QPushButton("")
        settings_btn.setIcon(qta.icon('fa5s.cog', color=c['text_primary']))
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.settings_clicked.emit)
        btn_row.addWidget(settings_btn)

        logout_btn = QPushButton("")
        logout_btn.setIcon(qta.icon('fa5s.sign-out-alt', color=c['text_primary']))
        logout_btn.setFixedSize(32, 32)
        logout_btn.setToolTip("Log Out")
        logout_btn.clicked.connect(self.logout_clicked.emit)
        btn_row.addWidget(logout_btn)
        
        layout.addLayout(btn_row)

    def _make_label(self, text, c):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {c['text_secondary']}; padding: 4px 8px;")
        return lbl

    def set_departments(self, departments):
        self.dept_list.clear()
        icon = qta.icon('fa5s.hashtag', color=get_colors()['text_secondary'])
        for d in departments:
            item = QListWidgetItem(f" {d['name']}")
            item.setIcon(icon)
            item.setData(Qt.ItemDataRole.UserRole, d)
            self.dept_list.addItem(item)

    def set_dm_users(self, users):
        self.dm_list.clear()
        for u in users:
            dot = {"online":"🟢","away":"🟡"}.get(u.get("presence","offline"),"⚫")
            item = QListWidgetItem(f"{dot} {u['display_name']}")
            item.setData(Qt.ItemDataRole.UserRole, u)
            self.dm_list.addItem(item)
            
    def increment_unread(self, ctype, cid):
        self._unread[ctype][cid] = self._unread[ctype].get(cid, 0) + 1
        self._update_item_text(ctype, cid)
        
    def clear_unread(self, ctype, cid):
        if cid in self._unread[ctype]:
            del self._unread[ctype][cid]
            self._update_item_text(ctype, cid)

    def _update_item_text(self, ctype, cid):
        lw = self.dept_list if ctype == "dept" else self.dm_list
        for i in range(lw.count()):
            item = lw.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data["id"] == cid:
                count = self._unread[ctype].get(cid, 0)
                badge = f" ({count})" if count > 0 else ""
                if ctype == "dept":
                    item.setText(f" {data['name']}{badge}")
                else:
                    dot = {"online":"🟢","away":"🟡"}.get(data.get("presence","offline"),"⚫")
                    item.setText(f"{dot} {data['display_name']}{badge}")
                break

    def show_admin_button(self, v): self.admin_btn.setVisible(v)

    def _on_dept(self, cur, prev):
        if cur:
            d = cur.data(Qt.ItemDataRole.UserRole)
            if d: 
                self.clear_unread("dept", d["id"])
                self.department_selected.emit(d["id"], d["name"])
                self.dm_list.clearSelection()

    def _on_dm(self, cur, prev):
        if cur:
            u = cur.data(Qt.ItemDataRole.UserRole)
            if u: 
                self.clear_unread("dm", u["id"])
                self.dm_selected.emit(u["id"], u["display_name"])
                self.dept_list.clearSelection()
