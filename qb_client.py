import logging
import requests
from typing import Dict

class QbClient:
    def __init__(self):
        self.session = requests.Session()

    def _login(self, base_url: str, username: str, password: str) -> bool:
        r = self.session.post(f"{base_url}/api/v2/auth/login", data={"username": username, "password": password})
        if r.status_code != 200:
            logging.error("qBittorrent login failed: %s %s", r.status_code, r.text)
            return False
        return True

    def apply_action(self, base_url: str, username: str, password: str, action: str) -> bool:
        if not base_url:
            logging.error("qb base url missing")
            return False
        try:
            if not self._login(base_url, username, password):
                return False
            if action == "delete":
                r = self.session.post(f"{base_url}/api/v2/torrents/delete", data={"hashes": "all", "deleteFiles": False})
            elif action == "pause":
                r = self.session.post(f"{base_url}/api/v2/torrents/pause", data={"hashes": "all"})
            elif action == "resume":
                r = self.session.post(f"{base_url}/api/v2/torrents/resume", data={"hashes": "all"})
            else:
                logging.error("unknown qb action %s", action)
                return False
            if r.status_code != 200:
                logging.error("qb action %s failed: %s %s", action, r.status_code, r.text)
                return False
            return True
        except Exception as exc:
            logging.error("qb action exception: %s", exc)
            return False
