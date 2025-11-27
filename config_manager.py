import json
import os
from threading import Lock
from typing import Any, Dict

DEFAULT_CONFIG = {
    "soap_wsdl_url": "",
    "netcup_accounts": [],
    "poll_interval_seconds": 600,
    "telegram": {"bot_token": "", "chat_id": ""},
    "qb_settings": {
        "use_scp_ip": True,
        "manual_host": "",
        "port": 9090,
        "username": "",
        "password": "",
        "restore_on_normal": True
    },
    "scp": {
        "host": "",
        "port": 22,
        "username": "",
        "password": "",
        "remote_ip_path": "",
        "poll_interval_seconds": 300
    },
    "throttle_action": "pause",  # pause | delete
    "log_retention_days": 7,
    "vertex": {
        "config_path": "",
        "downloader_key": "",
        "disable_value": "false",
        "enable_value": "true",
        "disable_command": "",
        "enable_command": "",
        "host": "",
        "port": 22,
        "username": "",
        "password": "",
        "api_url": "",
        "api_key": "",
        "downloader_id": "",
    }
}

class ConfigManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.path = os.path.join(base_dir, "config.json")
        self._lock = Lock()
        self._config: Dict[str, Any] = {}
        self.load()

    def _merge_defaults(self, data: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for key, value in default.items():
            if isinstance(value, dict):
                merged[key] = self._merge_defaults(data.get(key, {}), value)
            else:
                merged[key] = data.get(key, value)
        for key, value in data.items():
            if key not in merged:
                merged[key] = value
        return merged

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not os.path.exists(self.path):
                self._config = DEFAULT_CONFIG.copy()
                self.save()
            else:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = self._merge_defaults(data, DEFAULT_CONFIG)
        return self._config

    def save(self) -> None:
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._config))

    def update(self, new_conf: Dict[str, Any]) -> None:
        with self._lock:
            self._config.update(new_conf)
            self.save()

    def set_last_scp_ip(self, ip: str) -> None:
        with self._lock:
            self._config.setdefault("qb_settings", {})["last_scp_ip"] = ip
            self.save()

    def get_qb_host(self) -> str:
        cfg = self.get()
        qb = cfg.get("qb_settings", {})
        if qb.get("use_scp_ip") and qb.get("last_scp_ip"):
            return qb.get("last_scp_ip")
        return qb.get("manual_host", "")
