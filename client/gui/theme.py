"""Theme engine — Dark/Light/System theme management for PySide6."""

import darkdetect
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from client.config import client_config


# ─── Color Palettes ──────────────────────────────────────────────────────────

DARK_COLORS = {
    "bg_primary": "#1e1e2e",     # Base
    "bg_secondary": "#181825",   # Mantle
    "bg_tertiary": "#313244",    # Surface0
    "bg_hover": "#45475a",       # Surface1
    "bg_selected": "#585b70",    # Surface2
    "text_primary": "#cdd6f4",   # Text
    "text_secondary": "#bac2de", # Subtext1
    "text_muted": "#a6adc8",     # Subtext0
    "accent": "#cba6f7",         # Mauve
    "accent_hover": "#b4befe",   # Sapphire
    "accent_light": "rgba(203, 166, 247, 0.15)",
    "success": "#a6e3a1",        # Green
    "warning": "#f9e2af",        # Yellow
    "error": "#f38ba8",          # Red
    "border": "#313244",
    "input_bg": "#11111b",       # Crust
    "message_own": "rgba(203, 166, 247, 0.15)",
    "message_other": "#313244",
    "online": "#a6e3a1",
    "away": "#f9e2af",
    "offline": "#6c7086",
}

LIGHT_COLORS = {
    "bg_primary": "#eff1f5",     # Base
    "bg_secondary": "#e6e9ef",   # Mantle
    "bg_tertiary": "#ccd0da",    # Surface0
    "bg_hover": "#bcc0cc",       # Surface1
    "bg_selected": "#acb0be",    # Surface2
    "text_primary": "#4c4f69",   # Text
    "text_secondary": "#5c5f77", # Subtext1
    "text_muted": "#6c6f85",     # Subtext0
    "accent": "#8839ef",         # Mauve
    "accent_hover": "#7287fd",   # Sapphire
    "accent_light": "rgba(136, 57, 239, 0.12)",
    "success": "#40a02b",        # Green
    "warning": "#df8e1d",        # Yellow
    "error": "#d20f39",          # Red
    "border": "#ccd0da",
    "input_bg": "#ffffff",       # Crust
    "message_own": "rgba(136, 57, 239, 0.12)",
    "message_other": "#e6e9ef",
    "online": "#40a02b",
    "away": "#df8e1d",
    "offline": "#9ca0b0",
}


def get_colors() -> dict:
    """Get current color palette based on theme setting."""
    theme = client_config.theme
    if theme == "system":
        try:
            system_theme = darkdetect.theme()
            return DARK_COLORS if system_theme and system_theme.lower() == "dark" else LIGHT_COLORS
        except Exception:
            return DARK_COLORS
    return DARK_COLORS if theme == "dark" else LIGHT_COLORS


def apply_theme(app: QApplication):
    """Apply theme palette to application."""
    colors = get_colors()
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(colors["bg_primary"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["bg_secondary"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["bg_primary"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["bg_tertiary"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text_primary"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["bg_tertiary"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["text_muted"]))

    app.setPalette(palette)


def get_stylesheet() -> str:
    """Generate global QSS stylesheet."""
    c = get_colors()
    return f"""
        * {{
            font-family: "Segoe UI", sans-serif;
        }}
        QMainWindow, QDialog {{
            background-color: {c['bg_primary']};
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c['input_bg']};
            color: {c['text_primary']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {c['accent']};
        }}
        QPushButton {{
            background-color: {c['bg_tertiary']};
            color: {c['text_primary']};
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {c['bg_hover']};
        }}
        QPushButton:pressed {{
            background-color: {c['bg_selected']};
        }}
        QScrollBar:vertical {{
            background: {c['bg_secondary']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['bg_tertiary']};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['bg_hover']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            height: 0px;
        }}
        QLabel {{
            color: {c['text_primary']};
        }}
        QListWidget {{
            background-color: {c['bg_secondary']};
            border: none;
            outline: none;
            font-size: 14px;
        }}
        QListWidget::item {{
            padding: 10px 14px;
            border-radius: 8px;
            margin: 4px 8px;
        }}
        QListWidget::item:hover {{
            background-color: {c['bg_hover']};
        }}
        QListWidget::item:selected {{
            background-color: {c['bg_tertiary']};
            color: {c['accent']};
            font-weight: bold;
        }}
        QSplitter::handle {{
            background-color: {c['border']};
            width: 1px;
        }}
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background-color: {c['bg_tertiary']};
            color: {c['text_secondary']};
            padding: 8px 16px;
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {c['accent']};
            color: white;
        }}
    """
