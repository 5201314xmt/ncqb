import logging
from pathlib import Path

import paramiko

class VertexManager:
    def __init__(
        self,
        config_path: str,
        downloader_key: str,
        enable_value: str,
        disable_value: str,
        host: str = "",
        port: int = 22,
        username: str = "",
        password: str = "",
    ):
        self.config_path = config_path
        self.downloader_key = downloader_key
        self.enable_value = enable_value
        self.disable_value = disable_value
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def _toggle(self, enable: bool) -> None:
        if not self.config_path or not self.downloader_key:
            return

        if self.host:
            self._toggle_remote(enable)
        else:
            self._toggle_local(enable)

    def _toggle_local(self, enable: bool) -> None:
        path = Path(self.config_path)
        if not path.exists():
            logging.error("vertex config not found: %s", self.config_path)
            return
        try:
            content = path.read_text(encoding="utf-8")
            new_content = self._swapped_content(content, enable)
            if new_content != content:
                path.write_text(new_content, encoding="utf-8")
        except Exception as exc:
            logging.error("update vertex config failed: %s", exc)

    def _toggle_remote(self, enable: bool) -> None:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.host,
                port=self.port or 22,
                username=self.username or None,
                password=self.password or None,
            )
            with ssh.open_sftp() as sftp:
                with sftp.open(self.config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = self._swapped_content(content, enable)
                if new_content != content:
                    with sftp.open(self.config_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
        except Exception as exc:
            logging.error("update remote vertex config failed: %s", exc)

    def _swapped_content(self, content: str, enable: bool) -> str:
        if enable:
            return content.replace(
                self.downloader_key + "=" + self.disable_value,
                self.downloader_key + "=" + self.enable_value,
            )
        return content.replace(
            self.downloader_key + "=" + self.enable_value,
            self.downloader_key + "=" + self.disable_value,
        )

    def disable(self):
        self._toggle(False)

    def enable(self):
        self._toggle(True)
