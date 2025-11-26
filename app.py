# -------- app.py 内容开始 --------
import os
import json
import logging
from flask import Flask, render_template, jsonify
from monitor import ThrottleMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    wsdl_url = config["soap_wsdl_url"]
    accounts = config["netcup_accounts"]
    qb_map = config.get("qb_map", {})
    telegram_cfg = config.get("telegram", {})
    interval = config.get("poll_interval_seconds", 600)

    monitor = ThrottleMonitor(wsdl_url, accounts, qb_map, telegram_cfg, interval)
    monitor.start_in_background()

    app = Flask(__name__)
    app.monitor = monitor

    @app.route("/")
    def index():
        status = app.monitor.get_snapshot()
        total = len(status)
        throttled = sum(1 for s in status.values() if s["throttled"])
        normal = total - throttled
        return render_template("index.html",
                               status=status,
                               total=total,
                               throttled=throttled,
                               normal=normal)

    @app.route("/api/status")
    def api_status():
        status = app.monitor.get_snapshot()
        return jsonify(status)

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
# -------- app.py 内容结束 --------
