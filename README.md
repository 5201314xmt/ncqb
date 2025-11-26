# Netcup Throttle Guard

一键部署在 Debian 12 的 Netcup VPS 限速守护。自动轮询 Netcup SOAP 接口，当检测到限速时：

- 按配置暂停或删除 qBittorrent 种子，并通知 Telegram
- 通过 Vertex 配置文件开关下载器，避免继续推送到限速节点
- 通知仅在状态变化时发送，执行失败也会提醒
- 支持通过 SCP 拉取 qB Web IP（默认端口 9090），也可手动覆盖
- 配置写入本地 `config.json`，可选自动同步到 GitHub 仓库
- Web 面板可在线修改配置、查看日志并设置日志保留天数

## 一键部署（Debian 12）
```bash
# 安装依赖
sudo apt update
sudo apt install -y python3 python3-venv git

# 克隆并启动
git clone https://github.com/your/repo.git netcup-throttle-guard
cd netcup-throttle-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py  # 或部署为 systemd/pm2
```
首次运行会自动生成 `config.json`（无需手动创建），也可以在面板填写 GitHub Token/仓库信息后自动推送配置到远端。

## Web 面板
- 访问 `http://服务器IP:8000`
- 配置 Netcup 账户、Telegram、qB 登录、SCP 文件路径、GitHub 同步和 Vertex 开关
- 日志页 `/logs` 支持查看最近 500 行，按配置天数自动清理

## Vertex 联动
在面板填写 Vertex 配置文件路径与下载器键名：
- 限速时把 `键名=可用值` 替换为 `键名=禁用值`
- 恢复后再替换回去
- 若 Vertex 不在同一台 VPS，可填写远程主机、端口、SSH 用户和密码，通过 SFTP 直接改写远程配置文件

## GitHub 配置存储
启用后填写 `owner/repo`、分支和路径，保存时会通过 GitHub API 写入（需 PAT）。

## 其他
- 如需 systemd，请创建 service 调用 `.venv/bin/python app.py`
- qB Web 默认端口 9090，可在面板修改
