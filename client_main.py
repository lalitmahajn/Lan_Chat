"""Client entry point — login then main chat window."""

import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication

from client.config import client_config
from client.gui.theme import apply_theme, get_stylesheet
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app)
    app.setStyleSheet(get_stylesheet())

    # Check for saved session
    if not client_config.is_logged_in:
        login = LoginWindow()
        if login.exec() != LoginWindow.Accepted:
            sys.exit(0)

    # Show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
