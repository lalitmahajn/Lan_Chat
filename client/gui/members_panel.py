"""Members panel — collapsible right panel showing department members."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget
from client.gui.theme import get_colors


class MembersPanel(QWidget):
    user_clicked = Signal(int, str)  # user_id, display_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._build_ui()

    def _build_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        self.setStyleSheet(f"background-color: {c['bg_secondary']};")

        header = QLabel("👥 Members")
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {c['text_secondary']}; padding: 4px;")
        layout.addWidget(header)

        self.member_list = QListWidget()
        self.member_list.itemClicked.connect(self._on_click)
        layout.addWidget(self.member_list)

    def set_members(self, members: list[dict]):
        self.member_list.clear()
        # Sort: online first, then away, then offline
        order = {"online": 0, "away": 1, "offline": 2}
        members_sorted = sorted(members, key=lambda m: order.get(m.get("presence", "offline"), 2))

        for m in members_sorted:
            p = m.get("presence", "offline")
            dot = {"online": "🟢", "away": "🟡"}.get(p, "⚫")
            role_tag = " 👑" if m.get("role") == "admin" else ""
            item = QListWidgetItem(f"{dot} {m['display_name']}{role_tag}")
            item.setData(Qt.ItemDataRole.UserRole, m)
            self.member_list.addItem(item)

    def _on_click(self, item):
        m = item.data(Qt.ItemDataRole.UserRole)
        if m:
            self.user_clicked.emit(m["id"], m["display_name"])
