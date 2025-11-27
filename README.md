# Netcup Throttle Guard

一键部署在 Debian 12 的 Netcup VPS 限速守护。自动轮询 Netcup SOAP 接口，当检测到限速时：

- 按配置暂停或删除 qBittorrent 种子，并通知 Telegram
- 通过 Vertex API 优先开关下载器，失败时回退到命令/配置文件改写，避免继续推送到限速节点
- 通知仅在状态变化时发送，执行失败也会提醒
- 支持通过 SCP 拉取 qB Web IP（默认端口 9090），也可手动覆盖
- 配置写入本地 `config.json`
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
首次运行会自动生成 `config.json`（无需手动创建），可在面板直接维护全部配置。

## Web 面板
- 访问 `http://服务器IP:45671`
- 配置 Netcup 账户（支持多账号）、Telegram、qB 登录、SCP 文件路径和 Vertex 开关
- 日志页 `/logs` 支持查看最近 500 行，按配置天数自动清理

## Vertex 联动
推荐直接使用 Vertex API：
- 填写 Vertex API 地址（如 `https://vertex.example.com`）、API Key、下载器 ID。
- 限速时调用 `POST /api/v1/downloaders/{id}` 传 `{enabled: false}`，恢复时传 `{enabled: true}`。
- 点击“获取 ID 列表”可测试连接并列出下载器，确认 API 与凭证无误。

如 API 不可用，仍可使用回退方式：
- 配置文件改写：提供配置文件路径、下载器键名和启用/禁用值，支持 SSH 远程 SFTP 改写。
- 自定义命令：填写“启用/禁用命令”，本地直接执行；若填写了远程主机信息，则通过 SSH 执行，可配合容器 `docker exec` 或脚本。

## Netcup 账户
在配置面板中可以添加多个账户，每行填写登录名、密码和可选的备注标签，保存后将轮询所有账户名下的 VPS。

## 其他
- 如需 systemd，请创建 service 调用 `.venv/bin/python app.py`
- qB Web 默认端口 9090，可在面板修改
