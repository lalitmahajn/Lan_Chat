"""Server entry point — setup wizard (if first run) then start server + GUI."""

import logging
import sys
import threading
from pathlib import Path

import uvicorn
from PySide6.QtWidgets import QApplication

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

from server.config import get_db_path, server_config
from server.gui.setup_wizard import SetupWizard
from server.gui.server_window import ServerWindow
from server.app import create_app


logger = logging.getLogger("lan_chat")


def is_first_run() -> bool:
    """Check if DB exists."""
    return not Path(get_db_path()).exists()


def start_uvicorn(port: int):
    """Start FastAPI server in background thread."""
    app = create_app()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette for server GUI
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#181825"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1e2e"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#313244"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#313244"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#cdd6f4"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#7c3aed"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    port = server_config.server_port

    # First run check
    if is_first_run():
        wizard = SetupWizard()
        wizard.setup_complete.connect(lambda p: None)  # port updated in config
        result = wizard.exec()
        if result != SetupWizard.Accepted:
            sys.exit(0)
        port = server_config.server_port

    # Start Uvicorn in daemon thread
    server_thread = threading.Thread(
        target=start_uvicorn,
        args=(port,),
        daemon=True,
    )
    server_thread.start()
    logger.info(f"Server starting on port {port}...")

    # Show dashboard
    window = ServerWindow()
    window.stop_requested.connect(app.quit)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
