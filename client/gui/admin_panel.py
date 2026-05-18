"""Admin panel — user approval, department management (super_admin only)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget, QSpinBox,
    QComboBox,
)
from client.api_client import api_client
from client.gui.theme import get_colors

class DeptMembersDialog(QDialog):
    def __init__(self, dept, parent=None):
        super().__init__(parent)
        self.dept = dept
        self.setWindowTitle(f"Manage Members - {dept['name']}")
        self.setMinimumSize(400, 300)
        self._build_ui()
        self._load()

    def _build_ui(self):
        c = get_colors()
        l = QVBoxLayout(self)
        self.list = QListWidget()
        l.addWidget(self.list)
        
        row = QHBoxLayout()
        self.users_combo = QComboBox()
        row.addWidget(self.users_combo, 1)
        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self._add_user)
        row.addWidget(add_btn)
        l.addLayout(row)
        
        del_btn = QPushButton("Remove Selected")
        del_btn.clicked.connect(self._remove_user)
        l.addWidget(del_btn)

    def _load(self):
        self.list.clear()
        self.users_combo.clear()
        try:
            members = api_client.get_department_members(self.dept["id"])
            member_ids = set()
            for m in members:
                role_str = m.get('role', 'member')
                item = QListWidgetItem(f"{m['display_name']} (@{m['username']}) - {role_str}")
                item.setData(Qt.ItemDataRole.UserRole, m)
                self.list.addItem(item)
                member_ids.add(m["id"])
                
            all_users = api_client.get_approved_users()
            for u in all_users:
                if u["id"] not in member_ids:
                    self.users_combo.addItem(f"{u['display_name']} (@{u['username']})", u)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _add_user(self):
        data = self.users_combo.currentData()
        if not data: return
        try:
            api_client.add_department_member(self.dept["id"], data["id"], "member")
            self._load()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _remove_user(self):
        item = self.list.currentItem()
        if not item: return
        m = item.data(Qt.ItemDataRole.UserRole)
        try:
            api_client.remove_department_member(self.dept["id"], m["id"])
            self._load()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))


class AdminPanel(QDialog):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛡️ Admin Panel")
        self.setMinimumSize(600, 450)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # ─── Pending Approvals ────────
        pending_tab = QWidget()
        pl = QVBoxLayout(pending_tab)
        self.pending_list = QListWidget()
        pl.addWidget(self.pending_list)
        btn_row = QHBoxLayout()
        approve_btn = QPushButton("✅ Approve")
        approve_btn.setStyleSheet(f"background:{c['success']}; color:black; border-radius:6px; padding:6px 16px;")
        approve_btn.clicked.connect(self._approve)
        btn_row.addWidget(approve_btn)
        reject_btn = QPushButton("❌ Reject")
        reject_btn.setStyleSheet(f"background:{c['error']}; color:white; border-radius:6px; padding:6px 16px;")
        reject_btn.clicked.connect(self._reject)
        btn_row.addWidget(reject_btn)
        pl.addLayout(btn_row)
        tabs.addTab(pending_tab, "⏳ Pending")

        # ─── Departments ─────────────
        dept_tab = QWidget()
        dl = QVBoxLayout(dept_tab)
        self.dept_list = QListWidget()
        dl.addWidget(self.dept_list)
        add_row = QHBoxLayout()
        self.dept_name_input = QLineEdit()
        self.dept_name_input.setPlaceholderText("New department name")
        add_row.addWidget(self.dept_name_input)
        add_btn = QPushButton("+ Create")
        add_btn.setStyleSheet(f"background:{c['accent']}; color:white; border-radius:6px; padding:6px 16px;")
        add_btn.clicked.connect(self._create_dept)
        add_row.addWidget(add_btn)
        manage_btn = QPushButton("👥 Members")
        manage_btn.clicked.connect(self._manage_dept_members)
        add_row.addWidget(manage_btn)
        
        del_btn = QPushButton("🗑 Delete")
        del_btn.clicked.connect(self._delete_dept)
        add_row.addWidget(del_btn)
        dl.addLayout(add_row)
        tabs.addTab(dept_tab, "🏢 Departments")

        # ─── Users ────────────────────
        users_tab = QWidget()
        ul = QVBoxLayout(users_tab)
        self.users_list = QListWidget()
        ul.addWidget(self.users_list)
        tabs.addTab(users_tab, "👥 Users")

        # ─── Server Config ────────────
        config_tab = QWidget()
        cl = QFormLayout(config_tab)
        
        self.cfg_name = QLineEdit()
        self.cfg_max_size = QSpinBox()
        self.cfg_max_size.setRange(1, 1024)
        self.cfg_retention = QSpinBox()
        self.cfg_retention.setRange(0, 3650)
        self.cfg_idle = QSpinBox()
        self.cfg_idle.setRange(1, 1440)
        
        cl.addRow("Server Name:", self.cfg_name)
        cl.addRow("Max File Size (MB):", self.cfg_max_size)
        cl.addRow("Retention (Days, 0=Forever):", self.cfg_retention)
        cl.addRow("Idle Timeout (Mins):", self.cfg_idle)
        
        save_cfg_btn = QPushButton("💾 Save Config")
        save_cfg_btn.setStyleSheet(f"background:{c['accent']}; color:white; border-radius:6px; padding:6px 16px; margin-top: 10px;")
        save_cfg_btn.clicked.connect(self._save_config)
        cl.addRow("", save_cfg_btn)
        
        tabs.addTab(config_tab, "⚙️ Config")

        layout.addWidget(tabs)

    def _load_data(self):
        try:
            # Pending
            self.pending_list.clear()
            for u in api_client.get_pending_users():
                item = QListWidgetItem(f"{u['display_name']} (@{u['username']})")
                item.setData(Qt.ItemDataRole.UserRole, u)
                self.pending_list.addItem(item)

            # Users
            self.users_list.clear()
            for u in api_client.get_all_users():
                status_icon = {"approved":"✅","pending":"⏳","rejected":"❌"}.get(u["status"],"?")
                item = QListWidgetItem(f"{status_icon} {u['display_name']} (@{u['username']}) [{u['role']}]")
                item.setData(Qt.ItemDataRole.UserRole, u)
                self.users_list.addItem(item)
            # Departments
            self.dept_list.clear()
            for d in api_client.get_departments():
                item = QListWidgetItem(f"🏢 {d['name']}")
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.dept_list.addItem(item)
                
            # Config
            cfg = api_client.get_server_config()
            self.cfg_name.setText(cfg.get("server_name", "LAN Chat"))
            self.cfg_max_size.setValue(cfg.get("max_file_size_mb", 50))
            self.cfg_retention.setValue(cfg.get("retention_days", 30))
            self.cfg_idle.setValue(cfg.get("idle_timeout_minutes", 15))

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _approve(self):
        item = self.pending_list.currentItem()
        if not item: return
        u = item.data(Qt.ItemDataRole.UserRole)
        try:
            api_client.approve_user(u["id"])
            self._load_data()
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _reject(self):
        item = self.pending_list.currentItem()
        if not item: return
        u = item.data(Qt.ItemDataRole.UserRole)
        try:
            api_client.reject_user(u["id"])
            self._load_data()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _create_dept(self):
        name = self.dept_name_input.text().strip()
        if not name: return
        try:
            api_client.create_department(name)
            self.dept_name_input.clear()
            self._load_data()
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _delete_dept(self):
        item = self.dept_list.currentItem()
        if not item: return
        d = item.data(Qt.ItemDataRole.UserRole)
        try:
            api_client.delete_department(d["id"])
            self._load_data()
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _manage_dept_members(self):
        item = self.dept_list.currentItem()
        if not item: return
        d = item.data(Qt.ItemDataRole.UserRole)
        dlg = DeptMembersDialog(d, self)
        dlg.exec()
        self.data_changed.emit()

    def _save_config(self):
        try:
            updates = {
                "server_name": self.cfg_name.text().strip(),
                "max_file_size_mb": self.cfg_max_size.value(),
                "retention_days": self.cfg_retention.value(),
                "idle_timeout_minutes": self.cfg_idle.value(),
            }
            api_client.update_server_config(**updates)
            QMessageBox.information(self, "Success", "Server config updated.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
