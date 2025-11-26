import base64
import json
import logging
from typing import Dict, Optional
import requests

GITHUB_API = "https://api.github.com"

class GithubStorage:
    def push_config(self, config: Dict, cfg: Optional[Dict] = None) -> None:
        meta = cfg or config.get("github_storage", {})
        if not meta.get("enabled"):
            return
        token = meta.get("token")
        repo = meta.get("repo")
        path = meta.get("path", "config.json")
        branch = meta.get("branch", "main")
        if not token or not repo:
            logging.warning("Github storage enabled but token/repo missing")
            return
        url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}
        sha = None
        try:
            r = requests.get(url, headers=headers, params={"ref": branch})
            if r.status_code == 200:
                sha = r.json().get("sha")
        except Exception as exc:
            logging.error("Fetch github config failed: %s", exc)
        content = base64.b64encode(
            json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")
        payload = {
            "message": "Update config.json from netcup throttle guard",
            "content": content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        try:
            r = requests.put(url, headers=headers, json=payload)
            if r.status_code not in (200, 201):
                logging.error("Github push failed: %s %s", r.status_code, r.text)
        except Exception as exc:
            logging.error("Github push exception: %s", exc)

    def pull_config(self, cfg: Dict) -> Optional[Dict]:
        token = cfg.get("token")
        repo = cfg.get("repo")
        path = cfg.get("path", "config.json")
        branch = cfg.get("branch", "main")
        if not token or not repo:
            return None
        headers = {"Authorization": f"token {token}"}
        url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
        try:
            r = requests.get(url, headers=headers, params={"ref": branch})
            if r.status_code != 200:
                logging.error("Github pull failed: %s %s", r.status_code, r.text)
                return None
            data = r.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            return json.loads(content)
        except Exception as exc:
            logging.error("Github pull exception: %s", exc)
            return None
