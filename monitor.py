import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import paramiko
from scp import SCPClient

from config_manager import ConfigManager
from netcup_client import NetcupClient
from qb_client import QbClient
from telegram_notifier import TelegramNotifier
from vertex_manager import VertexManager

LOG_PATH = Path("logs/app.log")

class ThrottleMonitor:
    def __init__(self, cfg_manager: ConfigManager, notifier: TelegramNotifier):
        self.cfg_manager = cfg_manager
        cfg = cfg_manager.get()
        self.nc = NetcupClient(cfg.get("soap_wsdl_url"))
        self.qb = QbClient()
        self.notifier = notifier
        self.state: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.vertex = self._build_vertex(cfg)

    def _build_vertex(self, cfg: Dict) -> VertexManager:
        vcfg = cfg.get("vertex", {})
        return VertexManager(
            vcfg.get("config_path", ""),
            vcfg.get("downloader_key", ""),
            vcfg.get("enable_value", "true"),
            vcfg.get("disable_value", "false"),
            vcfg.get("host", ""),
            vcfg.get("port", 22),
            vcfg.get("username", ""),
            vcfg.get("password", ""),
        )

    def start(self):
        threading.Thread(target=self._netcup_loop, daemon=True).start()
        threading.Thread(target=self._scp_loop, daemon=True).start()
        threading.Thread(target=self._log_cleanup_loop, daemon=True).start()

    def _netcup_loop(self):
        while not self.stop_event.is_set():
            try:
                self.check_throttle()
            except Exception as exc:
                logging.error("netcup loop error: %s", exc)
            time.sleep(self.cfg_manager.get().get("poll_interval_seconds", 600))

    def _scp_loop(self):
        while not self.stop_event.is_set():
            cfg = self.cfg_manager.get().get("scp", {})
            interval = cfg.get("poll_interval_seconds", 300)
            try:
                if cfg.get("host") and cfg.get("remote_ip_path"):
                    ip = self._fetch_ip_via_scp(cfg)
                    if ip:
                        self.cfg_manager.set_last_scp_ip(ip.strip())
                        logging.info("SCP updated qB IP to %s", ip.strip())
            except Exception as exc:
                logging.error("scp loop error: %s", exc)
            time.sleep(interval)

    def _log_cleanup_loop(self):
        while not self.stop_event.is_set():
            retention = self.cfg_manager.get().get("log_retention_days", 7)
            try:
                self._cleanup_logs(retention)
            except Exception as exc:
                logging.error("log cleanup error: %s", exc)
            time.sleep(86400)

    def _cleanup_logs(self, retention_days: int):
        cutoff = datetime.now() - timedelta(days=retention_days)
        if LOG_PATH.exists():
            lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
            kept = []
            for line in lines:
                try:
                    ts = line.split(" - ")[0]
                    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")
                    if dt >= cutoff:
                        kept.append(line)
                except Exception:
                    kept.append(line)
            LOG_PATH.write_text("\n".join(kept), encoding="utf-8")

    def _fetch_ip_via_scp(self, cfg: Dict) -> str:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(cfg.get("host"),
                    port=cfg.get("port", 22),
                    username=cfg.get("username"),
                    password=cfg.get("password"))
        with SCPClient(ssh.get_transport()) as scp:
            local_tmp = Path("/tmp/qb_ip.txt")
            scp.get(cfg.get("remote_ip_path"), local_tmp)
            return local_tmp.read_text(encoding="utf-8")

    def check_throttle(self):
        cfg = self.cfg_manager.get()
        new_status = self.nc.fetch_status_for_accounts(cfg.get("netcup_accounts", []))
        qb_cfg = cfg.get("qb_settings", {})
        action = cfg.get("throttle_action", "pause")
        base_url = self._build_qb_url(cfg)
        username = qb_cfg.get("username", "")
        password = qb_cfg.get("password", "")
        with self.lock:
            for ip, info in new_status.items():
                old = self.state.get(ip)
                self.state[ip] = info
                if info.get("throttled"):
                    if not old or not old.get("throttled"):
                        self._handle_throttle(base_url, username, password, action, ip, info)
                else:
                    if old and old.get("throttled"):
                        self._handle_restore(base_url, username, password, action, ip, info, qb_cfg)

    def _build_qb_url(self, cfg: Dict) -> str:
        host = self.cfg_manager.get_qb_host()
        port = cfg.get("qb_settings", {}).get("port", 9090)
        if not host:
            return ""
        if host.startswith("http"):
            return f"{host}:{port}" if host.endswith(str(port)) is False else host
        return f"http://{host}:{port}"

    def _handle_throttle(self, base_url: str, username: str, password: str, action: str, ip: str, info: Dict):
        message_parts = [f"⚠ VPS 限速: {ip} ({info.get('name')})"]
        qb_ok = False
        if base_url:
            qb_ok = self.qb.apply_action(base_url, username, password, action)
            if qb_ok:
                message_parts.append(f"qB {action} 成功")
            else:
                message_parts.append(f"qB {action} 失败")
        if self.vertex:
            self.vertex.disable()
            message_parts.append("已关闭 Vertex 下载器")
        self.notifier.send(" | ".join(message_parts))
        logging.info("Throttle triggered for %s: %s", ip, message_parts)

    def _handle_restore(self, base_url: str, username: str, password: str, action: str, ip: str, info: Dict, qb_cfg: Dict):
        message_parts = [f"✅ VPS 恢复: {ip} ({info.get('name')})"]
        qb_ok = True
        if action == "pause" and qb_cfg.get("restore_on_normal", True) and base_url:
            qb_ok = self.qb.apply_action(base_url, username, password, "resume")
            message_parts.append("qB resume 成功" if qb_ok else "qB resume 失败")
        if self.vertex:
            self.vertex.enable()
            message_parts.append("已恢复 Vertex 下载器")
        self.notifier.send(" | ".join(message_parts))
        logging.info("Throttle recovered for %s: %s", ip, message_parts)

    def get_snapshot(self):
        with self.lock:
            return dict(self.state)
