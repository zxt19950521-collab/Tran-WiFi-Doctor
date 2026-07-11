# CASE-035: Mesh 频繁 POOR_RCPI ping-pong 漫游 + wpa 认证失败导致 TikTok 打不开

## 基本信息
- **案例ID**: CASE-035
- **分类**: disconnect
- **来源**: TOS163-39774
- **创建时间**: 2026-07-11
- **匹配次数**: 0

## 现象描述
- 孟加拉粉丝反馈：**TikTok app not opening**，同 WiFi 下其他 App 能加载（Facebook/YouTube 等）
- 机型 **TECNO CN6c**，HiOS 16.3.0 / Android 16，MTK 平台
- 问题时间 2026-06-25 **19:55:16 ~ 19:55:41**（Asia/Dhaka）；用户 19:56:17 手动关 WiFi
- SSID **RINMUS  WIFI 620**（双频 mesh 同 ESS：`:65` 2.4G ch10 / `:67` 5G ch153，网关 192.168.1.1）
- 视频对齐窗口 19:55:12 ~ 19:56:11；同 AP 三星手机正常（待对比复现）

## 根因结论
**RINMUS WIFI 620 mesh 覆盖弱、两 AP RSSI 接近，MTK 驱动整段连接期间因 POOR_RCPI 在 `:65`/`:67` 间 ping-pong 漫游 21 次（PER=0）；问题当次 19:55:16 漫游至 `:67` 后驱动 L2 SUCCESS 但 wpa 层 Auth 超时（Associated ≠ CONNECTED），叠加回退 `:65` 4-Way 卡在 2/4 超时，导致 TikTok 启动窗口 ~25 s 无 CONNECTED，Feed/API 无法发出。**

`:67` 于 19:55:41 恢复 CONNECTED 后，19:56:08/16 仍触发 POOR_RCPI 漫游（L2 FAIL / ABORT），说明 ping-pong 为慢性问题。

机理链条：
1. 整段 **21 次** `ROAM_DISCOVERY reason=POOR_RCPI`，RCPI 常见 **62~63（-79 dBm）**，Thr **64（-78 dBm）**，PER 全程 **0**
2. 候选 AP RSSI 仅比当前好 **1~9 dBm**，`SSID_BEST_RSSI` 策略导致 `:65↔:67` ping-pong；漫游后 RSSI 多数未改善
3. **19:55:06** 第 1 次 CONNECTED `:65` → **19:55:16** POOR_RCPI 漫游 assoc `:67`（驱动 L2 SUCCESS 252 ms）
4. **19:55:16~26** 仅 Associated，**无 4-Way** → **19:55:26 Auth 超时 DISCONNECT**
5. **19:55:28** assoc `:65` → 4-Way 卡 **2/4** → **19:55:40** 超时（WRONG_KEY 误报）→ DISCONNECT
6. **19:55:18** Ping `{success=false, time=1000ms}`；TikTok 19:55:16 启动时 wpa 无 CONNECTED
7. **19:55:41** 第 2 次 CONNECTED `:67` → 19:55:45 validated；**19:56:08/16** 仍 POOR_RCPI（#20 无候选 L2 FAIL，#21 `:67→:65` L2 FAIL + ROAMING ABORT，与用户关 WiFi 同期）

**判据**：只有 `CTRL-EVENT-CONNECTED` + 4-Way 完成才算 WiFi 真正连上；`Associated` ≠ 连上。

## 排查步骤
1. main_log 查 wpa 连接链：`CTRL-EVENT-CONNECTED` / `Associated` / `Authentication timed out` / `4-Way Handshake failed`
2. kernel_log 查 `ROAM_DISCOVERY reason=POOR_RCPI`、RCPI/Thr、CURR/CAND RSSI、`kalRoamingReport` SUCCESS/FAIL
3. **合并多个 kernel log 文件**（本案例 #20/#21 在 `kernel_log_9`，#1~19 在 `kernel_log_17`；单看 log_17 会漏统计）
4. 交叉验证 L3：Ping / Probe / DNS 与 wpa CONNECTED 窗口对齐
5. events log 对齐 TikTok 启动时间与 wpa 状态
6. 排除密码错误（19:55:06/41 均 4-Way 成功）、PER 触发漫游（PER=0）、框架 tear down

## 关键日志
```
// 19:55:06 — 第 1 次 CONNECTED（:65）
19:55:06.420  CTRL-EVENT-CONNECTED - Connection to :65 completed

// 19:55:16 — POOR_RCPI 漫游（驱动 L2 SUCCESS，wpa 未 CONNECTED）
19:55:16.418  ROAM_DISCOVERY reason=POOR_RCPI RCPI[62(-79)] Thr[64(-78)] PER[0]
19:55:16.611  SEARCH_DONE Selected :67 RSSI[-70]  (CURR :65 RSSI[-79])
19:55:16.671  kalRoamingReport: SUCCESS :65->:67 ch10->153 252ms
19:55:16.684  Associated with 08:8a:f1:08:b4:67
19:55:26.686  Authentication with :67 timed out
19:55:26.708  CTRL-EVENT-DISCONNECTED locally_generated=1

// 19:55:28~40 — 重连 :65 失败
19:55:28.041  Associated with 08:8a:f1:08:b4:65
19:55:30.008  WPA: Sending EAPOL-Key 2/4
19:55:40.004  Authentication with :65 timed out
19:55:40.007  WPA: 4-Way Handshake failed

// 19:55:41 — 第 2 次 CONNECTED（:67）
19:55:41.749  CTRL-EVENT-CONNECTED - Connection to :67 completed

// L3 验证
19:55:18.444  Ping result: {success=false, time=1000ms}
19:55:52.941  Ping result: {success=true, time=21ms}

// 19:56:08~16 — CONNECTED :67 后仍 POOR_RCPI（kernel_log_9）
19:56:08.267  ROAM_DISCOVERY reason=POOR_RCPI RCPI[62(-79)] Thr[63(-79)]  CURR :67 RSSI[-82]
19:56:09.875  kalRoamingReport: FAIL 1608ms  :67→00:00  RSSI -66→0
19:56:16.868  ROAM_DISCOVERY reason=POOR_RCPI RCPI[59(-81)] Thr[64(-78)]  CURR :67 RSSI[-81] CAND :65 -70
19:56:17.433  kalRoamingReport: FAIL 568ms  :67→:65  Fail reason 2
19:56:17.928  ROAMING ABORT

// 19:56:17 — 用户关 WiFi
19:56:17.930  CTRL-EVENT-DISCONNECTED :67 locally_generated=1
```

## TAG
- POOR_RCPI
- 乒乓漫游
- Mesh-PingPong
- 同ESS多BSSID
- Associated-Not-Connected
- Driver-L2-Success-Wpa-Auth-Fail
- 4-Way-Handshake-Timeout
- Auth超时
- SSID_BEST_RSSI
- RCPI劣化
- TikTok
- 特定App打不开
- validated与可用性脱节
- CN6c
- MTK driver
- 孟加拉
- 粉丝反馈

## 建议措施
1. **P0**：排查 RINMUS WIFI 620 mesh AP 覆盖/位置、5G ch153 backhaul、固件版本
2. **P0**：**固定 BSSID 测试**（仅连 `:65` 或 `:67`），观察是否仍 POOR_RCPI / Auth 超时
3. **P1**：评估漫游策略：RCPI 阈值、ping-pong 抑制、漫游后 wpa 认证重试
4. **P1**：改 DNS（8.8.8.8 / Private DNS Off），排除网关 DNS 慢响应
5. **P2**：同 AP 对比 CN6c vs 三星，抓 wpa + tcpdump

## 数据局限
- 无 tcpdump，无法确认 TikTok API TCP 成败
- 无 wlanLinkQualityMonitor，无法量化 PER/吞吐曲线
- 漫游统计需合并 kernel_log_17 + kernel_log_9；main_log_3（19:55:31 起）缺 19:55:06~30

## 相关案例
- **CASE-014**（双频 mesh POOR_RCPI 乒乓漫游 + WRONG_KEY 断网）— 高匹配
- **CASE-012**（系统 validated + 特定 App 体验差）— 部分匹配
- **CASE-019**（Probe fail + SSID ping-pong）— 部分匹配
