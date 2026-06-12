# CASE-014: 游戏大流量触发双频误漫游 WRONG_KEY 导致 network lost（Roblox Error 277）

## 基本信息
- **案例ID**: CASE-014
- **分类**: disconnect
- **来源**: TOS163-35926
- **创建时间**: 2026-06-12
- **匹配次数**: 0

## 现象描述
- 印尼粉丝反馈：玩 Roblox **游戏渲染时 WiFi 突然断开**（jaringan wifi saat render game tiba tiba terputus），截图 **Error Code 277**
- 机型 LK7（TECNO），hios16.3.0 / Android 16，MTK 平台
- 偶现（once）；问题时间 2026-06-10 **18:57:16**（Asia/Jakarta）
- SSID **UNIVERSAL**（双频同 ESS：`:c8` 2.4G ch1 / `:d0` 5G ch40，网关 192.168.1.1）
- WiFi 约 **7s** 后恢复 validated，但 Roblox 会话已断开

## 根因结论
**Roblox 渲染/资产大流量下载（kernel Tput 峰值 ~36 Mbps）期间，MTK 驱动因 RCPI 劣化（-69）触发 2.4G→5G 误漫游（:c8→:d0）；`scanCalculateTotalScore` 加权模型偏好 5G（BD+200）且用扫描态 cRSSI 低估当前 AP，选中实际更弱的 5G BSS 后 4-Way 握手失败（WRONG_KEY），叠加框架层 `Wifi network lost` 约 7s，导致 Roblox Error 277。**

后续 19:07–19:20 在同一 ESS 上形成 **2.4G/5G 乒乓漫游**（9 次 L2 切换），虽无第二次断网，但影响游戏稳定性。

机理链条：
1. 故障前强信号 **-48~-50 dBm**，链路 **720/722 Mbps**，游戏高负载 Tput **~36 Mbps**
2. PER 间歇升至 **13~21%**，RCPI 劣化到 **-69**（Online Scan 将当前 :c8 测为 -69，非 get_station 的 -50）
3. `apsSearchBssDescByScore` 选 :d0（5G，Score **1178** vs :c8 **730**），Reason=5 触发漫游
4. 连上 :d0 后 RSSI **-60**、Rx **10 Mbps**；**4s 后 WRONG_KEY** → disconnect reason=15
5. **18:57:27** `Probe null` → `Ping null` → **`Wifi network lost`**；Roblox WebSocket/HTTP `Network is unreachable`
6. **18:57:34** validated 恢复，network ID **191→192**；**18:57:49** 用户仍见 Error 277
7. 后续 **19:07–19:20** 在 :c8/:d0 间乒乓切换 9 次，2 次 `roamingFsmRunEventFail`，无第二次 network lost

## 排查步骤
1. 框架层（main_log）对齐 Roblox 高负载与 `Wifi network lost` 时间 → 确认 L3 断连与游戏报错同秒
2. 驱动层（kernel_log，**+7h 对齐 Jakarta**）查 `roamingFsmRunEventDiscovery`、BSSID 切换、link speed 坍塌
3. 查 `apsSearchBssDescByScore` / `scanCalculateTotalScore` 评分拆解（BD/RSSI/IT/BW 各维度）
4. 查 wpa_supplicant `4-Way Handshake failed` / `WRONG_KEY` / `SSID-TEMP-DISABLED`
5. 统计全程 `roam=Status` 与 wpa `Associated` 事件，区分致命漫游 vs 乒乓漫游
6. 排除 `tear down wlan0`（CASE-012 路径）、蜂窝切换、纯应用 Bug

## 关键日志
```
// 故障前：强信号 + 游戏大流量
06-10 18:57:17.652  TranWifiSmartAssistantController: ====>>rssi :-50
[kernel +7h] 11:57:17  get_station: link speed=720/722, rssi=-50, BSSID:[1c:61:**:**:c8]
[kernel +7h] 11:57:18  kalPerMonUpdate: Tput: 37527248(35.807mbps)

// 漫游选型：5G 总分碾压（1178 vs 730）
[kernel +7h] 11:57:22.633  roamingFsmRunEventDiscovery: RCPI 82(-69) Reason[5]
[kernel +7h] 11:57:22.633  apsSearchBssDescByScore: :c8 cRSSI[-69] Score 730
[kernel +7h] 11:57:22.633  apsSearchBssDescByScore: :d0 cRSSI[-60] Score 1178 BD[200]
[kernel +7h] 11:57:22.753  get_station: link speed=650/10, rssi=-60, BSSID:[1c:61:**:**:d0]

// WRONG_KEY + network lost
06-10 18:57:26.864  wpa_supplicant: 4-Way Handshake failed - pre-shared key may be incorrect
06-10 18:57:27.324  WifiStatistics:WifiNetworkCheck: Ping result: null
06-10 18:57:27.344  WifiStatistics:WifiNetworkCheck: Wifi network lost
06-10 18:57:27.088  Roblox: CURLINFO_OS_ERRNO: 101 Network is unreachable
[kernel +7h] 11:57:27.732  kalPerMonUpdate: Tput: 0(0.000mbps) idle:1

// 恢复 validated
06-10 18:57:34.038  TranWifiSmartAssistantController: mValidated = true

// 后续乒乓漫游（示例）
[kernel +7h] 12:15:40  roam :c8→:d0 RCPI -79 Reason[0]
[kernel +7h] 12:15:42  roamingFsmRunEventFail: EVENT-ROAMING FAIL reason 1
[kernel +7h] 12:15:44  roam :d0→:c8 Reason[7]
```

## TAG
- 双频误漫游
- scanCalculateTotalScore
- 5G频段加分BD200
- RSSI劣化
- PER高
- 物理速率坍塌
- WRONG_KEY
- network lost
- 乒乓漫游
- 同ESS多BSSID
- 游戏断网
- Roblox
- MTK driver
- LK7
- 印度尼西亚

## 建议措施
1. **漫游策略优化（优先）**：游戏白名单场景评估提高 RCPI 漫游门限或抑制 Online Scan 触发的跨频段漫游
2. **评分模型**：高负载时用连接态 RSSI 校正扫描态 cRSSI；评估 5G BD+200 在双频 Mesh 下的过激偏好
3. **认证路径**：检查 UNIVERSAL 2.4G/5G BSS 安全配置一致性（WRONG_KEY 是否 PMF/PSK 协商异常）
4. **游戏场景**：前台游戏时抑制乒乓漫游（19:07–19:20 共 9 次切换仍影响 fps）
5. **复现**：连接 UNIVERSAL，Roblox 重资源场景 + tcpdump 抓漫游窗口游戏端口断流

## 数据局限
- 仅有 main_log + kernel_log（两份 TagLog）；缺 tcpdump、空口抓包
- SecurityPay 扫描显示 :d0=-75 dBm 弱于 :c8=-56，与驱动评分用 cRSSI 存在口径差异
- 19:07 后切 :d0 握手成功，首次 WRONG_KEY 可能与高负载时序有关，待复现确认

## 相关案例
- **CASE-006**（弱信号 + 漫游导致速率坍塌 + 游戏卡顿，但 WiFi 未断开）— 高匹配
- **TOS163-35489**（LK7 `network lost` + gateway 变更，无明确驱动漫游）— 中高匹配
- **CASE-008**（强信号下空口拥塞导致 Roblox 加载慢，无断开）— 部分匹配
