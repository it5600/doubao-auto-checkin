# doubao-auto-checkin

豆包工作「免费用豆包」每日自动签到，**纯云端无头浏览器**，不依赖自己的电脑开机。

- 每天自动签到领 +200 额度（周一翻倍）
- 基于 [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)（Playwright 的 CDP 层反检测 fork）
- 伪装 Windows 桌面指纹：NVIDIA WebGL / Win32 / 1536×864@1.25 / 上海时区 / SamanthaDoubaoWork UA
- 自动点击签到按钮 + 自动领取「待领」奖励
- 直连 detail 接口复核累计额度与连续签到天数

## 原理

签到入口是豆包客户端内嵌页 `https://www.doubao.com/pc/agent-explore`。直接裸 HTTP 调签到写接口会被风控（710010702），必须用真实浏览器环境 + 完整指纹走一遍页面交互。本脚本用 Patchright 在 CDP 协议层消除自动化痕迹，再用 init script 补齐 WebGL/平台/语言等指纹，通过写接口校验。

## 安装

```bash
pip install -r requirements.txt
patchright install chromium
```

> Linux 服务器建议加 `--with-deps` 安装系统依赖。

## 配置 Cookie

浏览器登录 doubao.com 后，从开发者工具 Network 任意请求头复制完整 `Cookie`，二选一：

**方式一：环境变量（推荐，不入库）**
```bash
export DOUBAO_COOKIE="sid_guard=...; sessionid=...; ..."
```

**方式二：项目根目录 config.json**
```json
{"cookie": "sid_guard=...; sessionid=...; ..."}
```

> Cookie 有效期约 18 天（sid_guard），到期需重新登录更新。config.json 已在 .gitignore 中，勿提交。

## 运行

```bash
python3 scripts/checkin.py
```

日志追加写入 `checkin.log`，异常自动截图 `error_*.png`。末尾会输出：
```
RESULT total=4700 today=True continuous=7 last=2026-11-13
```

## 定时执行（systemd / cron）

```cron
# 每天早上 7:00 签到
0 7 * * *  DOUBAO_COOKIE="sid_guard=..." /usr/bin/python3 /path/to/scripts/checkin.py >> /path/to/cron.log 2>&1
```

## 故障码

| 返回码 | 含义 | 处理 |
|---|---|---|
| code=0 | 正常 | — |
| 710012001 | Cookie 过期 | 重新登录更新 Cookie |
| 710010702 | 写接口风控 | 检查指纹补丁是否被活动侧升级，勿反复重试 |
| 页面「仅支持电脑版」 | UA 不对 | 确认使用脚本内置 SamanthaDoubaoWork UA |

## 免责声明
仅用于个人账号每日签到自动化，请遵守豆包用户协议，勿用于批量养号。
