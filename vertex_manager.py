import logging
from pathlib import Path
import subprocess

import paramiko

class VertexManager:
    def __init__(
        self,
        config_path: str,
        downloader_key: str,
        enable_value: str,
        disable_value: str,
        enable_command: str = "",
        disable_command: str = "",
        host: str = "",
        port: int = 22,
        username: str = "",
        password: str = "",
    ):
        self.config_path = config_path
        self.downloader_key = downloader_key
        self.enable_value = enable_value
        self.disable_value = disable_value
        self.enable_command = enable_command
        self.disable_command = disable_command
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def _toggle(self, enable: bool) -> bool:
        command = self.enable_command if enable else self.disable_command
        if command:
            return self._run_command(command)

        if not self.config_path or not self.downloader_key:
            return True

        if self.host:
            return self._toggle_remote(enable)
        return self._toggle_local(enable)

    def _toggle_local(self, enable: bool) -> bool:
        path = Path(self.config_path)
        if not path.exists():
            logging.error("vertex config not found: %s", self.config_path)
            return False
        try:
            content = path.read_text(encoding="utf-8")
            new_content = self._swapped_content(content, enable)
            if new_content != content:
                path.write_text(new_content, encoding="utf-8")
            return True
        except Exception as exc:
            logging.error("update vertex config failed: %s", exc)
            return False

    def _toggle_remote(self, enable: bool) -> bool:
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
            return True
        except Exception as exc:
            logging.error("update remote vertex config failed: %s", exc)
            return False

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

    def _run_command(self, command: str) -> bool:
        try:
            if self.host:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=self.host,
                    port=self.port or 22,
                    username=self.username or None,
                    password=self.password or None,
                )
                _, stdout, stderr = ssh.exec_command(command)
                exit_code = stdout.channel.recv_exit_status()
                out = stdout.read().decode().strip()
                err = stderr.read().decode().strip()
                if exit_code != 0:
                    logging.error(
                        "vertex remote command failed (%s): %s",
                        exit_code,
                        err or out,
                    )
                    return False
                if out:
                    logging.info("vertex remote command output: %s", out)
                return True

            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                logging.error("vertex command failed (%s): %s", proc.returncode, proc.stderr or proc.stdout)
                return False
            if proc.stdout:
                logging.info("vertex command output: %s", proc.stdout.strip())
            return True
        except Exception as exc:
            logging.error("run vertex command error: %s", exc)
            return False

    def disable(self) -> bool:
        return self._toggle(False)

    def enable(self) -> bool:
        return self._toggle(True)
