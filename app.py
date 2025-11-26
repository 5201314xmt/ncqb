import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash

from config_manager import ConfigManager
from monitor import ThrottleMonitor, LOG_PATH
from telegram_notifier import TelegramNotifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)


def create_app():
    cfg_manager = ConfigManager(BASE_DIR)
    cfg_manager.sync_from_github()
    cfg = cfg_manager.get()

    notifier = TelegramNotifier(cfg.get("telegram", {}).get("bot_token", ""), cfg.get("telegram", {}).get("chat_id", ""))
    monitor = ThrottleMonitor(cfg_manager, notifier)
    monitor.start()

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "netcup-guard")
    app.monitor = monitor
    app.cfg_manager = cfg_manager

    @app.route("/")
    def index():
        status = app.monitor.get_snapshot()
        total = len(status)
        throttled = sum(1 for s in status.values() if s.get("throttled"))
        normal = total - throttled
        return render_template(
            "index.html",
            status=status,
            total=total,
            throttled=throttled,
            normal=normal,
            cfg=app.cfg_manager.get(),
        )

    @app.route("/api/status")
    def api_status():
        status = app.monitor.get_snapshot()
        return jsonify(status)

    @app.route("/config", methods=["POST"])
    def update_config():
        data = request.form.to_dict()
        cfg = app.cfg_manager.get()
        qb_settings = cfg.get("qb_settings", {})
        qb_settings.update({
            "use_scp_ip": data.get("use_scp_ip") == "on",
            "manual_host": data.get("manual_host", ""),
            "port": int(data.get("qb_port", qb_settings.get("port", 9090))),
            "username": data.get("qb_username", ""),
            "password": data.get("qb_password", ""),
            "restore_on_normal": data.get("restore_on_normal") == "on",
        })
        scp_cfg = cfg.get("scp", {})
        scp_cfg.update({
            "host": data.get("scp_host", ""),
            "port": int(data.get("scp_port", scp_cfg.get("port", 22))),
            "username": data.get("scp_username", ""),
            "password": data.get("scp_password", ""),
            "remote_ip_path": data.get("scp_remote", ""),
            "poll_interval_seconds": int(data.get("scp_interval", scp_cfg.get("poll_interval_seconds", 300)))
        })
        git_cfg = cfg.get("github_storage", {})
        git_cfg.update({
            "enabled": data.get("github_enabled") == "on",
            "token": data.get("github_token", ""),
            "repo": data.get("github_repo", ""),
            "branch": data.get("github_branch", "main"),
            "path": data.get("github_path", "config.json")
        })
        vertex_cfg = cfg.get("vertex", {})
        vertex_cfg.update({
            "config_path": data.get("vertex_path", ""),
            "downloader_key": data.get("vertex_key", ""),
            "enable_value": data.get("vertex_enable", "true"),
            "disable_value": data.get("vertex_disable", "false"),
            "enable_command": data.get("vertex_enable_cmd", ""),
            "disable_command": data.get("vertex_disable_cmd", ""),
            "host": data.get("vertex_host", ""),
            "port": int(data.get("vertex_port", vertex_cfg.get("port", 22))),
            "username": data.get("vertex_username", ""),
            "password": data.get("vertex_password", ""),
            "api_url": data.get("vertex_api_url", ""),
            "api_key": data.get("vertex_api_key", ""),
            "downloader_id": data.get("vertex_downloader_id", ""),
        })
        new_conf = {
            "soap_wsdl_url": data.get("soap_wsdl_url", cfg.get("soap_wsdl_url")),
            "netcup_accounts": [
                {
                    "loginName": data.get("nc_login", ""),
                    "password": data.get("nc_password", ""),
                    "label": data.get("nc_label", "") or data.get("nc_login", "")
                }
            ],
            "poll_interval_seconds": int(data.get("poll_interval_seconds", cfg.get("poll_interval_seconds", 600))),
            "telegram": {
                "bot_token": data.get("tg_token", ""),
                "chat_id": data.get("tg_chat_id", ""),
            },
            "qb_settings": qb_settings,
            "scp": scp_cfg,
            "throttle_action": data.get("throttle_action", cfg.get("throttle_action", "pause")),
            "log_retention_days": int(data.get("log_retention_days", cfg.get("log_retention_days", 7))),
            "github_storage": git_cfg,
            "vertex": vertex_cfg,
        }
        app.cfg_manager.update(new_conf, push_to_github=True)
        app.monitor.refresh_vertex()
        flash("配置已更新并写入本地/GitHub")
        return redirect(url_for("index"))

    @app.route("/api/test_vertex", methods=["GET"])
    def test_vertex():
        app.monitor.refresh_vertex()
        vertex = app.monitor.vertex
        if not vertex:
            return jsonify({"ok": False, "error": "Vertex 未配置"}), 400
        downloaders = vertex.list_downloaders()
        if not downloaders:
            return jsonify({"ok": False, "error": "获取下载器列表失败"}), 400
        simplified = [
            {"id": d.get("id"), "name": d.get("name"), "enabled": d.get("enabled")}
            for d in downloaders
        ]
        return jsonify({"ok": True, "downloaders": simplified})

    @app.route("/logs")
    def logs():
        if LOG_PATH.exists():
            lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
            lines = lines[-500:]
        else:
            lines = []
        return render_template("logs.html", lines=lines)

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
