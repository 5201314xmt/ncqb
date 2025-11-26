import logging
from pathlib import Path

class VertexManager:
    def __init__(self, config_path: str, downloader_key: str, enable_value: str, disable_value: str):
        self.config_path = config_path
        self.downloader_key = downloader_key
        self.enable_value = enable_value
        self.disable_value = disable_value

    def _toggle(self, enable: bool) -> None:
        if not self.config_path or not self.downloader_key:
            return
        path = Path(self.config_path)
        if not path.exists():
            logging.error("vertex config not found: %s", self.config_path)
            return
        try:
            content = path.read_text(encoding="utf-8")
            if enable:
                new_content = content.replace(self.downloader_key + "=" + self.disable_value,
                                              self.downloader_key + "=" + self.enable_value)
            else:
                new_content = content.replace(self.downloader_key + "=" + self.enable_value,
                                              self.downloader_key + "=" + self.disable_value)
            if new_content != content:
                path.write_text(new_content, encoding="utf-8")
        except Exception as exc:
            logging.error("update vertex config failed: %s", exc)

    def disable(self):
        self._toggle(False)

    def enable(self):
        self._toggle(True)
