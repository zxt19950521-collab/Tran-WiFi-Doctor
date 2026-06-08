# CASE-006: 弱信号 + 单 AP 漫游失败导致游戏卡顿（WiFi 未断开）

## 基本信息
- **案例ID**: CASE-006
- **分类**: performance
- **来源**: LK7OS163-2073
- **创建时间**: 2026-06-05
- **匹配次数**: 0

## 现象描述
- 印尼粉丝反馈：WiFi 连接整体还算流畅，但**玩游戏 / 用某些 App 偶现卡顿**，本次发生在实时对战游戏 Bleach Brave Souls
- 机型 LK7（TECNO），hios16.3.0 / Android 16，MTK 平台，2.4G
- 偶现；问题时间 2026-06-01 10:43:15（雅加达），问题时刻捕获在日志末尾
- 关键：WiFi 全程未断开（用户主观"连接没断"），但游戏这类低延迟业务卡顿

## 根因结论
**弱信号 + 环境只有单个 AP，导致空口 PER 飙升、物理速率坍塌，叠加 driver 反复触发"无目标"漫游全频扫描，使低延迟敏感业务（游戏）卡顿；但 WiFi 始终未断开，故用户感觉"连接还算流畅"。**

机理链条：
1. RSSI 从 -52~-56 劣化到 -66/-68/-69 dBm
2. 链路 PER 高达 85~93%，物理速率从 650/722Mbps 坍塌到 65/10Mbps（RX 10Mbps 为最低档）
3. driver 因 PER/RSSI 触发漫游探测，但环境仅 1 个 AP（`in 1 BSSes` / `Can't roam out` / 只能选回自己），漫游连续失败（`roamingFsmRunEventFail` / `No target found, try to full scan again`）
4. 每轮漫游 discovery 触发全频扫描，STA 离开数据信道 → 数据中断百毫秒级，叠加本就差的空口质量 → 游戏卡顿
5. 全程 BSSID 稳定、TxOK/RxOK 持续增长、框架层 `Wifi network validated`、无 disconnect/deauth

## 排查步骤
1. 框架层（main_log）确认 WiFi 全程连接且校验通过、无断开/漫游切换 → 排除连接断开类问题
2. 驱动层（kernel_log）查 `mtk_cfg80211_get_station` 链路统计：发现 RSSI 劣化、link speed 坍塌到 65/10Mbps
3. 查 `roamingFsmProcessEvent` 发现 PER 高达 85~93%（远超门限 Thr 64/56）
4. 查 `apsSearchBssDescByScore` 发现 `in 1 BSSes` + `Can't roam out`，漫游 `roamingFsmRunEventFail`
5. 时间线对齐：RSSI 劣化 + PER 高 + 速率坍塌 + 漫游失败均聚集在问题时刻（~10:42:50-10:43:18）

## 关键日志
```
// 物理速率从 650/722 坍塌到 65/10，RSSI 劣化到 -68（kernel）
[464787] get_station: link speed=650/722, rssi=-60, BSSID:[98:03..5e]   // 早期正常
[464842] get_station: link speed=130/520, rssi=-68, TxFail=3
[464851] get_station: link speed=65/10,  rssi=-60                       // RX 速率跌到 10Mbps

// PER 高达 93% 触发漫游，但无更好 AP，漫游失败
[464872.430] roamingFsmProcessEvent: ROAMING_EVENT_DISCOVERY ... RCPI[82(-69)] PER[93] Thr[64(-78)] Reason[1]
[464872.657] apsSearchBssDescByScore: Can't roam out, try blocklist
[464872.657] apsSearchBssDescByScore: Selected 98:03..5e ... in 1 BSSes     // 环境仅 1 个 AP
[464872.657] aisSearchHandleBadBssDesc: [Roaming] No target found, try to full scan again
[464875.306] roamingFsmRunEventFail: EVENT-ROAMING FAIL: reason 1

// 框架层：WiFi 全程连接且校验通过、无断开（main_log）
10:41:03.910 WifiStatistics:WifiNetworkCheck: Wifi network validated
10:42:29.395 Choreographer: Skipped 41 frames! ... too much work on main thread
```

## TAG
- RSSI 劣化
- PER 高
- 物理速率坍塌
- 单 AP 漫游失败
- 漫游全频扫描抖动
- 2.4G 单频
- 无断开
- 游戏卡顿
- MTK driver

## 建议措施
1. 改善信号覆盖（首要）：靠近路由器 / 加装 AP·Mesh / 启用路由 5G 频段（当前仅连 2.4G）
2. 驱动侧优化漫游策略：单 AP 无候选时退避 / 抑制全频扫描频率，减少扫描对游戏数据的中断
3. 游戏 / 低延迟场景的扫描抑制：前台为游戏（GameSpace）时降低后台漫游扫描激进度或采用单信道扫描
4. 复测：本次为粉丝加密 TagLog，无 tcpdump / 空口 / WiFi FW(picus) 日志，建议 5G+2.4G 双频环境带 tcpdump / 空口抓包复测

## 数据局限
- 仅有 main_log + kernel_log；缺 tcpdump、空口抓包、WiFi FW(picus) 日志
- 结论基于 driver 链路统计（PER/速率/RSSI/漫游 FSM），未能从 IP 层 RTT/重传或空口帧直接坐实

## 相关案例
- 无（本案例为案例库首个 performance 类）
