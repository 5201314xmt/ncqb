import logging
from typing import Dict, List
from zeep import Client

class NetcupClient:
    def __init__(self, wsdl_url: str):
        self.client = Client(wsdl=wsdl_url)

    def fetch_status_for_accounts(self, accounts: List[Dict]) -> Dict[str, Dict]:
        status: Dict[str, Dict] = {}
        for acc in accounts:
            login = acc.get("loginName")
            password = acc.get("password")
            label = acc.get("label", login)
            if not login or not password:
                logging.warning("skip empty netcup account")
                continue
            try:
                vservers = self.client.service.getVServers(login, password)
            except Exception as e:
                logging.error("getVServers failed for %s: %s", login, e)
                continue
            for vps in vservers:
                try:
                    info = self.client.service.getVServerInformation(login, password, vps)
                    ip = info["ips"][0]
                    throttled = info["serverInterfaces"][0]["trafficThrottled"]
                    status[ip] = {"name": vps, "throttled": throttled, "owner": label}
                except Exception as e:
                    logging.error("getVServerInformation error: %s", e)
        return status
