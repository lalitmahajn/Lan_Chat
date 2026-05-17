"""System tray icon + toast notifications."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayManager:
    def __init__(self, parent_window):
        self._window = parent_window
        self._tray = QSystemTrayIcon(parent_window)
        self._tray.setIcon(self._make_icon())
        self._tray.setToolTip("LAN Chat")
        self._tray.activated.connect(self._on_activated)

        menu = QMenu()
        show_action = menu.addAction("Show")
        show_action.triggered.connect(self._show_window)
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(parent_window.close)
        self._tray.setContextMenu(menu)

    def show(self):
        self._tray.show()

    def hide(self):
        self._tray.hide()

    def notify(self, title: str, message: str):
        if self._tray.isVisible():
            self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _make_icon(self) -> QIcon:
        pm = QPixmap(32, 32)
        pm.fill(QColor("#7c3aed"))
        p = QPainter(pm)
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(pm.rect(), 0x0084, "💬")
        p.end()
        return QIcon(pm)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self._window.showNormal()
        self._window.activateWindow()
