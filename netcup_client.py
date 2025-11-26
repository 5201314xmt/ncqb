from zeep import Client
import logging

class NetcupClient:
    def __init__(self, wsdl_url):
        self.client = Client(wsdl=wsdl_url)

    def fetch_status_for_accounts(self, accounts):
        status = {}
        for acc in accounts:
            login = acc["loginName"]
            password = acc["password"]
            try:
                vservers = self.client.service.getVServers(login, password)
            except Exception as e:
                logging.error(f"getVServers failed: {e}")
                continue
            for vps in vservers:
                try:
                    info = self.client.service.getVServerInformation(login, password, vps)
                    ip = info["ips"][0]
                    throttled = info["serverInterfaces"][0]["trafficThrottled"]
                    status[ip] = {"name": vps, "throttled": throttled}
                except Exception as e:
                    logging.error(f"getVServerInformation error: {e}")
        return status
