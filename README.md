# GLaDOS & Railgun 自动签到与积分兑换蓝图 (Hermes Skill)

本项目包含用于自动执行 GLaDOS/Railgun 每日签到、查询会员剩余天数、总积分查询以及自动积分兑换套餐的生产级脚本，并提供一整套以 **Hermes Agent Skill** 规范编写的技能文档与运维说明。

---

## 📖 什么是 Hermes Agent Skill？
[Hermes Agent](https://hermes-agent.nousresearch.com/) 是一个前沿的 AI 智能体框架。技能（Skill）是其程序性记忆 of capabilities 的载体。
本项目中的 `SKILL.md` 遵循 Hermes 技能规范编写，将其导入到 Hermes Agent 后，**您的 AI 助手便能瞬间学会如何帮您配置、维护以及自动排查 GLaDOS 签到脚本的任何异常**。

---

## 📂 项目结构
* **`SKILL.md`**：Hermes Agent 技能主文档，包含了详细的运行逻辑、高频踩坑点（Cookie 截断、JSON 格式等）以及详细的故障排查步骤。
* **`scripts/checkin.py`**：核心自动签到与积分兑换 Python 脚本。
  - 支持多域名灾备自动轮询（`glados.cloud`, `railgun.info` 等）。
  - 支持多账号并发/轮询签到。
  - 支持积攒到指定点数（如 500 积分）自动兑换套餐。
  - 支持 PushDeer 实时移动端消息推送。
* **`scripts/checkin.sh`**：专为 crontab 等定时任务设计的 Shell 守护包装脚本，支持 3 次重试避错，成功后优雅返回 `exit 0`，失败时抛出异常。
* **`scripts/logging_config.py`** : 日志格式化工具，自动规范转换为北京时间输出。

---

## 🚀 快速上手部署

### 1. 本地手动运行
确保您已经安装了依赖项：
```bash
pip3 install requests pypushdeer
```

配置环境变量并运行脚本：
```bash
# 多个 Cookie 请使用 & 连接
export GLADOS_COOKIES="koa:sess=你的CookieA; koa:sess.sig=你的SigA & koa:sess=你的CookieB; koa:sess.sig=你的SigB"

# （可选）填入您的 PushDeer Key 即可在手机微信/App收到推送
export PUSHDEER_SENDKEY="PDBOX1234567..."

# 运行签到脚本
python3 scripts/checkin.py
```

### 2. 使用 Crontab 每日自动运行
您可以使用随附的守护脚本 `checkin.sh` 进行配置。
首先修改 `scripts/checkin.sh`，填入您的 `GLADOS_COOKIES` 和 `PUSHDEER_SENDKEY`。

接着在终端中运行：
```bash
crontab -e
```
添加以下一行，每天早上 8:30 自动执行签到（请将路径替换为您本机的绝对路径）：
```text
30 8 * * * /bin/bash /path/to/scripts/checkin.sh >> /path/to/checkin.log 2>&1
```

---

## 🤝 贡献与感谢
本项目遵循 MIT 协议开源。欢迎提交 Issue 和 PR 共同完善此自动签到技能！
