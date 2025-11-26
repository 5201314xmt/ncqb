import time
import threading
import logging
from netcup_client import NetcupClient
from qb_client import QbClient
from telegram_notifier import TelegramNotifier

class ThrottleMonitor:
    def __init__(self, wsdl_url, accounts, qb_map, telegram_cfg, interval):
        self.nc = NetcupClient(wsdl_url)
        self.qb = QbClient()
        self.notifier = TelegramNotifier(telegram_cfg["bot_token"],
                                         telegram_cfg["chat_id"])
        self.accounts = accounts
        self.qb_map = qb_map
        self.interval = interval
        self.status = {}
        self.lock = threading.Lock()

    def start_in_background(self):
        t = threading.Thread(target=self.loop, daemon=True)
        t.start()

    def loop(self):
        while True:
            self.check()
            time.sleep(self.interval)

    def check(self):
        new_status = self.nc.fetch_status_for_accounts(self.accounts)
        with self.lock:
            for ip, info in new_status.items():
                old = self.status.get(ip)
                self.status[ip] = info
                if info["throttled"]:
                    qb = self.qb_map.get(ip)
                    if qb:
                        self.qb.pause_all(qb)
                    self.notifier.send(f"⚠ VPS 限速: {ip} ({info['name']})")
                else:
                    if old and old["throttled"]:
                        self.notifier.send(f"✅ VPS 恢复: {ip} ({info['name']})")

    def get_snapshot(self):
        with self.lock:
            return dict(self.status)
