import logging
import requests

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, msg: str):
        if not self.token or not self.chat_id:
            logging.info("telegram not configured, skip msg: %s", msg)
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": msg})
        except Exception as e:
            logging.error(f"Telegram error: {e}")
