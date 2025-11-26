import requests
import logging

class QbClient:
    def pause_all(self, qb_conf):
        url = qb_conf["url"]
        user = qb_conf["username"]
        pw = qb_conf["password"]

        s = requests.Session()
        try:
            r = s.post(f"{url}/api/v2/auth/login",
                       data={"username": user, "password": pw})
            if r.status_code != 200:
                return False
            s.post(f"{url}/api/v2/torrents/pause",
                   data={"hashes": "all"})
            return True
        except Exception as e:
            logging.error(f"pause error: {e}")
            return False
