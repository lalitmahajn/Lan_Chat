"""REST API client — handles HTTP requests to server with token management."""

import logging
from typing import Optional

import httpx

from client.config import client_config

logger = logging.getLogger("lan_chat.api")


class APIClient:
    """Synchronous HTTP client for REST endpoints."""

    def __init__(self):
        self._client = httpx.Client(timeout=15.0)

    @property
    def _base(self) -> str:
        return client_config.server_url

    @property
    def _headers(self) -> dict:
        headers = {}
        if client_config.access_token:
            headers["Authorization"] = f"Bearer {client_config.access_token}"
        return headers

    def _refresh_if_needed(self, response: httpx.Response) -> bool:
        """If 401, try refresh. Returns True if refreshed."""
        if response.status_code != 401 or not client_config.refresh_token:
            return False
        try:
            r = self._client.post(
                f"{self._base}/api/auth/refresh",
                json={"refresh_token": client_config.refresh_token},
            )
            if r.status_code == 200:
                data = r.json()
                client_config.access_token = data["access_token"]
                client_config.refresh_token = data["refresh_token"]
                client_config.save()
                return True
        except Exception:
            pass
        return False

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make request with auto-refresh on 401."""
        url = f"{self._base}{path}"
        resp = self._client.request(method, url, headers=self._headers, **kwargs)
        if resp.status_code == 401 and self._refresh_if_needed(resp):
            resp = self._client.request(method, url, headers=self._headers, **kwargs)
        return resp

    # ─── Auth ─────────────────────────────────────────────────────────────

    def register(self, username: str, password: str, display_name: str) -> dict:
        r = self._client.post(f"{self._base}/api/auth/register", json={
            "username": username, "password": password, "display_name": display_name,
        })
        r.raise_for_status()
        return r.json()

    def login(self, username: str, password: str) -> dict:
        r = self._client.post(f"{self._base}/api/auth/login", json={
            "username": username, "password": password,
        })
        r.raise_for_status()
        return r.json()

    def logout(self):
        if client_config.refresh_token:
            try:
                self._request("POST", "/api/auth/logout", json={
                    "refresh_token": client_config.refresh_token,
                })
            except Exception:
                pass
        client_config.clear_auth()

    # ─── Messages ─────────────────────────────────────────────────────────

    def get_department_messages(self, dept_id: int, page: int = 1, limit: int = 50) -> dict:
        r = self._request("GET", f"/api/messages/{dept_id}", params={"page": page, "limit": limit})
        r.raise_for_status()
        return r.json()

    def get_dm_messages(self, user_id: int, page: int = 1, limit: int = 50) -> dict:
        r = self._request("GET", f"/api/messages/dm/{user_id}", params={"page": page, "limit": limit})
        r.raise_for_status()
        return r.json()

    # ─── Files ────────────────────────────────────────────────────────────

    def upload_file(self, filepath: str) -> dict:
        with open(filepath, "rb") as f:
            r = self._request("POST", "/api/files/upload", files={"file": f})
        r.raise_for_status()
        return r.json()

    def download_file(self, file_id: int) -> tuple[bytes, str]:
        """Returns (content_bytes, filename)."""
        r = self._request("GET", f"/api/files/{file_id}")
        r.raise_for_status()
        filename = "download"
        cd = r.headers.get("content-disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip('"')
        return r.content, filename

    def get_thumbnail(self, file_id: int) -> Optional[bytes]:
        try:
            r = self._request("GET", f"/api/files/{file_id}/thumbnail")
            if r.status_code == 200:
                return r.content
        except Exception:
            pass
        return None

    def get_my_departments(self) -> list:
        r = self._request("GET", "/api/departments")
        r.raise_for_status()
        return r.json()

    def get_department_members(self, dept_id: int) -> list:
        r = self._request("GET", f"/api/departments/{dept_id}/members")
        r.raise_for_status()
        return r.json()

    def get_approved_users(self) -> list:
        r = self._request("GET", "/api/users/approved")
        r.raise_for_status()
        return r.json()

    def get_me(self) -> dict:
        r = self._request("GET", "/api/me")
        r.raise_for_status()
        return r.json()

    # ─── Admin ────────────────────────────────────────────────────────────

    def get_pending_users(self) -> list:
        r = self._request("GET", "/api/admin/users/pending")
        r.raise_for_status()
        return r.json()

    def get_all_users(self) -> list:
        r = self._request("GET", "/api/admin/users")
        r.raise_for_status()
        return r.json()

    def approve_user(self, user_id: int) -> dict:
        r = self._request("POST", f"/api/admin/users/{user_id}/approve")
        r.raise_for_status()
        return r.json()

    def reject_user(self, user_id: int) -> dict:
        r = self._request("POST", f"/api/admin/users/{user_id}/reject")
        r.raise_for_status()
        return r.json()

    def get_departments(self) -> list:
        """Get all departments (admin)."""
        # Admin doesn't have a dedicated "list all depts" endpoint yet.
        # We can use the user-facing one for now, or just return empty
        # since we only need it to populate the list. Let's add it to admin_routes.
        r = self._request("GET", "/api/admin/departments")
        r.raise_for_status()
        return r.json()

    def create_department(self, name: str, description: str = "") -> dict:
        r = self._request("POST", "/api/admin/departments", json={
            "name": name, "description": description,
        })
        r.raise_for_status()
        return r.json()

    def delete_department(self, dept_id: int):
        r = self._request("DELETE", f"/api/admin/departments/{dept_id}")
        r.raise_for_status()

    def add_department_member(self, dept_id: int, user_id: int, role: str = "member") -> dict:
        r = self._request("POST", f"/api/admin/departments/{dept_id}/members", json={
            "user_id": user_id, "role": role,
        })
        r.raise_for_status()
        return r.json()

    def remove_department_member(self, dept_id: int, user_id: int):
        r = self._request("DELETE", f"/api/admin/departments/{dept_id}/members/{user_id}")
        r.raise_for_status()

    def get_server_config(self) -> dict:
        r = self._request("GET", "/api/admin/config")
        r.raise_for_status()
        return r.json()

    def update_server_config(self, **kwargs) -> dict:
        r = self._request("PUT", "/api/admin/config", json=kwargs)
        r.raise_for_status()
        return r.json()

    # ─── Health ───────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            r = self._client.get(f"{self._base}/api/health", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def close(self):
        self._client.close()


# Global instance
api_client = APIClient()
