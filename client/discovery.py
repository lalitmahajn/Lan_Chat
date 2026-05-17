"""mDNS server discovery using zeroconf."""

import logging
import socket
from typing import Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("lan_chat.discovery")

SERVICE_TYPE = "_lanchat._tcp.local."


class DiscoveryWorker(QThread):
    """Discover LAN Chat servers on the network."""

    server_found = Signal(str, int, str)  # host, port, server_name
    finished_scan = Signal()

    def __init__(self, timeout: float = 5.0, parent=None):
        super().__init__(parent)
        self.timeout = timeout

    def run(self):
        try:
            from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange

            found = []

            class Listener:
                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        host = socket.inet_ntoa(info.addresses[0]) if info.addresses else "127.0.0.1"
                        port = info.port
                        srv_name = info.properties.get(b"name", b"LAN Chat").decode()
                        found.append((host, port, srv_name))

                def remove_service(self, zc, type_, name):
                    pass

                def update_service(self, zc, type_, name):
                    pass

            zc = Zeroconf()
            listener = Listener()
            browser = ServiceBrowser(zc, SERVICE_TYPE, listener)

            # Wait for discovery
            import time
            time.sleep(self.timeout)

            zc.close()

            for host, port, name in found:
                self.server_found.emit(host, port, name)

        except Exception as e:
            logger.error(f"Discovery error: {e}")

        self.finished_scan.emit()


def register_service(port: int, server_name: str) -> Optional[object]:
    """Register server as mDNS service. Returns registration info (call unregister to stop)."""
    try:
        from zeroconf import Zeroconf, ServiceInfo
        import socket

        local_ip = _get_local_ip()
        info = ServiceInfo(
            SERVICE_TYPE,
            f"{server_name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties={"name": server_name},
        )
        zc = Zeroconf()
        zc.register_service(info)
        logger.info(f"mDNS service registered: {server_name} at {local_ip}:{port}")
        return (zc, info)
    except Exception as e:
        logger.error(f"mDNS registration failed: {e}")
        return None


def unregister_service(registration) -> None:
    """Unregister mDNS service."""
    if registration:
        zc, info = registration
        try:
            zc.unregister_service(info)
            zc.close()
        except Exception:
            pass


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
