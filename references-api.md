# 豆包签到接口与 DOM 参考

## 入口
- 签到面板：`https://www.doubao.com/pc/agent-explore`（客户端「免费用豆包」标签页内嵌）
- 有效 UA：`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.7727.149 Safari/537.36 SamanthaDoubaoWork/2.34.12`

## 读接口 detail
```
POST https://www.doubao.com/alice/ug/campaign/v3/detail/?version_code=23206&language=zh&device_platform=web&doubao_device_platform=web&aid=497858&real_aid=497858&pkg_type=release
Content-Type: application/json
Origin: https://www.doubao.com
Referer: https://www.doubao.com/
Cookie: <config.json cookie>
Body: {"campaign_group_code":"pc_incentive_task_mvp_v3"}
```
返回：
- `data.progress.total_amount` 累计额度
- `data.tasks[].campaign_code == "daily_signin"` → `daily_checkin.{checked_in_today, continuous_days, last_checkin_date, reward.reward_amount}`

## 写接口 checkin
```
POST .../alice/ug/campaign/landing/checkin?...
Body: {"scene":"pc_incentive_task_mvp_v3"}
```
由页面点击按钮触发，需浏览器内生成的 a_bogus/msToken 签名，裸 HTTP 重放会 710010702。

## DOM 选择器
- 签到卡片：`[data-reward-code="daily_signin"]`
- 已签标记：`.rewarded-nPpEuG`
- 可点按钮：卡片内 `button`（文字「立即签到」），成功后无按钮、出现 rewarded 标记
- 其他任务卡片：同样挂 `data-reward-code`，按钮文字「去完成」/「领取」

## 报错码
- `710012001`：登录过期（Cookie 失效）
- `710010702`：写接口风控/签名/环境校验失败

## 指纹对齐目标（Windows 真实环境）
- WebGL unmasked vendor: `Google Inc. (NVIDIA)`
- WebGL unmasked renderer: `ANGLE (NVIDIA, NVIDIA GeForce GTX 960 (0x00001401) Direct3D11 vs_5_0 ps_5_0, D3D11)`
- screen 1536×864 @ devicePixelRatio 1.25，availHeight 826
- languages: `zh-CN, en, en-GB, en-US, zh`
- timezone: `Asia/Shanghai`，platform: `Win32`，vendor: `Google Inc.`
