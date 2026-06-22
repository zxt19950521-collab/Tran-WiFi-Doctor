# 【CN6】【粉丝反馈】【菲律宾】强信号下 WiFi 偶现丢失 分析报告

**工单号**：TOS163-37795  
**关联案例**：CASE-019  
**状态**：Open  
**优先级**：Critical  
**分析时间**：2026-06-22  
**设备**：TECNO CN6（XYZ）/ 菲律宾  
**版本**：CN6-16.3.0.127(OP002PF001AZ)FANS  
**问题时间**：2026-06-18 **13:00:05**（Asia/Manila，粉丝申报）  
**反馈提交**：2026-06-18 13:02:00  
**用户原声**：sometime was lost a wifi signal while the wifi connect to the phone is very strong  
**发生概率**：偶现（occasional）  
**WiFi SSID**：**JRC RICE 5G**（5GHz ch52，BSSID `c8:5a:9f:ba:ab:b1`）  
**日志来源**：TagLog_2026_0618_125703 + TagLog_2026_0618_130007（OSS）

---

## 【日志完整性】

| 类型 | 状态 | 路径 |
|------|------|------|
| main log | ✅ 有 | `TagLog_.../main_log_22` + `main_log_43` |
| kernel log | ✅ 有 | `kernel_log_27` + `kernel_log_48`（已执行 kernel 时间转换） |
| radio log | ✅ 有 | `radio_log_23` + `radio_log_44` |
| tcpdump | ❌ 未提供 | — |
| 空口 log | ✅ 有 | `connsys_picus_log_35/56`（本次以框架/驱动断连日志为主分析） |

**分析局限性**：无 tcpdump，未逐帧解析 picus；但 main/kernel 日志已完整还原 SSID 乒乓与 validated 失效链路。

---

## 【项目匹配】

| 项 | 内容 |
|----|------|
| 匹配项目 | CN6 / 粉丝反馈 / WiFi 断连 / 强信号 |
| 匹配案例 | **CASE-019**（本案入库）/ **CASE-012**（`NetworkProbe` 失败 → network lost）— **高匹配** |
| 弱相关 | **CASE-014**（误漫游导致 network lost）— 本案为 **SSID 切换乒乓**，非 BSSID 漫游 |
| 分析依据 | `WifiStat:NetworkProbe` + `TranWifiSmartAssistant` 自动选网 + wpa_supplicant 断连事件 |

---

## 【总体统计】

| 指标 | 数值 |
|------|------|
| 故障窗口（核心） | **12:56:42 — 12:59:06**（约 **2.5 分钟**） |
| 申报时间 vs 日志 | 申报 **13:00:05** 时 WiFi **已恢复稳定**；实际断连潮在 **约 4 分钟前** |
| 故障前 RSSI | **-44 ~ -52 dBm**（强信号） |
| 故障前链路速率 | **3900/4333 Mbps**（kernel，5G） |
| `network lost` 次数 | **9 次**（12:56:53 — 12:59:00） |
| SSID 切换次数 | **9 次 CONNECT**（`JRC RICE 5G` ↔ `SHOAI2025_2.4G` 乒乓） |
| 断连原因 | **Reason=3 locally_generated**（本机主动断开，非 AP deauth） |
| Probe 失败 | `connectivitycheck.gstatic.com` **ConnectException** |
| 逐次连接探测有网 | **10 段会话**中 **6 次成功** / **4 次未完成**（见下表） |
| 验证耗时（成功时） | **0.8s ~ 20.3s**（多数 8~9s） |
| 13:00:05 状态 | **JRC RICE 5G**，`mValidated=true`，RSSI 监测正常，**无断连** |

---

## 【根因结论】

**非弱信号掉线，而是「互联网探测失败 → 框架判定 no-internet → TranWifiSmartAssistant 自动切网」引发的 SSID 乒乓断连。**

机理链条：

```
强信号 JRC RICE 5G（RSSI -47）
  → NetworkProbe 连接 connectivitycheck.gstatic.com 失败（ConnectException）
  → mValidated=false + Temporarily disabling network (no-internet)
  → TranWifiSmartAssistant 评分选网：SHOAI2025_2.4G(3622) > JRC RICE 5G(3540)
  → 本机主动 disconnect（reason=3）并关联到 SHOAI2025_2.4G
  → 两 SSID 反复切换（9 次 network lost / 9 次 CONNECT）
  → 其中 4 次短连接（<6s）未完成 EVER_EVALUATED，状态栏持续感叹号
  → 用户感知「WiFi 图标还在但信号丢失/无网」
  → 12:59 后回到 JRC RICE 5G 并 validated 恢复
```

**与用户描述一致**：物理层信号强（RSSI -40~-50），但 L3 层多次 `network lost`，UI 表现为 WiFi「丢失」。

---

## 【时间线详细分析】

### 阶段 1：故障前正常（12:52 — 12:56:41）

- 连接 **JRC RICE 5G**，`TranWifiSmartAssistant` RSSI **-44~-52 dBm**。
- 用户在使用问卷/游戏等应用，WiFi 图标显示强信号。
- kernel `link speed=3900/4333`，MovAvg_rssi **-49~-50**。

### 阶段 2：Probe 失败触发 validated 失效（12:56:42 — 12:56:43）— 根因起点

| 时间 | 事件 |
|------|------|
| **12:56:42.537** | `WifiStat:NetworkProbe: Probe failed` — `ConnectException: Failed to connect to connectivitycheck.gstatic.com/142.250.207.35:443` |
| **12:56:43.700** | `Wifi network unvalidated` |
| **12:56:43.707** | `mValidated = false` |
| **12:56:43.684** | `ConnectivityService: Update score for net 183 : -IS_VALIDATED` → **状态栏感叹号** |
| **12:56:43.745** | `WifiClientModeImpl: Temporarily disabling network because of no-internet access` |
| **12:56:47.091** | Ping 仍成功但 **260ms**（链路未完全断，但探测已失败） |

**关键点**：Probe 访问 Google 连通性检测服务器失败，可能因 AP/运营商 DNS 劫持、防火墙、或上游网络瞬断——**不等于 WiFi 射频弱**。

### 阶段 3：自动选网 + SSID 乒乓（12:56:49 — 12:59:00）— 断连潮

| 时间 | 事件 |
|------|------|
| 12:56:49 | `WifiNetworkQuality` 评分：JRC RICE 5G **3540** < SHOAI2025_2.4G **3622** |
| 12:56:49 | candidate = **SHOAI2025_2.4G**；当前 SSID 在 **blacklist**，但 `auto switch:false`（用户选定网络） |
| **12:56:52.669** | `WifiService: connect` — **`packageNameToUse=com.android.systemui`**（框架/SystemUI 发起连接，非用户手动点选） |
| **12:56:52.736** | `CTRL-EVENT-DISCONNECTED` **c8:5a:...:b1** reason=3 locally_generated |
| 12:56:52.840 | 尝试关联 **SHOAI2025_2.4G** |
| **12:56:53.015** | CONNECT **f8:64:b8:ef:d5:2b**（2.4G ch4，RSSI **-64**） |
| **12:56:53.044** | **`Wifi network lost`**（第 1 次） |
| 12:57:11 — 12:59:00 | 两 SSID **反复切换 8 次**，共 **9 次 network lost**；每次新 `net <id>` 先仅 `+TRANSPORT_PRIMARY`（**感叹号**），约 **9~30s** 后才 `+EVER_EVALUATED` |
| 12:57:16 | 回到 JRC RICE 5G 后再次 `no-internet access` 禁用 |

**BSSID 对照**：

| SSID | BSSID | 频段 | 故障时 RSSI |
|------|-------|------|------------|
| JRC RICE 5G | c8:5a:9f:ba:ab:b1 | 5GHz ch52 | **-45 ~ -51** |
| JRC RICE 5G | c8:5a:9f:ba:ab:b0 | 2.4GHz ch6 | -40 ~ -56（同组网） |
| SHOAI2025_2.4G | f8:64:b8:ef:d5:2b | 2.4GHz ch4 | **-64 ~ -71** |

### 【逐次连接后探测有网判定】

**判定依据**：

- `ConnectivityService: Update score for net <id> : +EVER_EVALUATED`（或 `+EVER_VALIDATED+IS_VALIDATED`）→ **探测有网**，状态栏无感叹号
- 仅有 `+TRANSPORT_PRIMARY`、出现 `-IS_VALIDATED`，或断线前未见 EVER_EVALUATED → **探测未完成/无网**，状态栏感叹号
- 辅以 `WifiStatistics:WifiNetworkCheck: Probe result` / `Wifi network validated` / `unvalidated`

**结论：不是每次连上 WiFi 后都完成有网探测。** 10 段会话中 **6 次**在断线前完成验证，**4 次**因在线过短（<6s）被 SystemUI 切走而未完成。

| # | 连接时间 | SSID | net | 在线时长 | 探测有网 | EVER_EVALUATED | 说明 |
|---|----------|------|-----|----------|----------|----------------|------|
| 1 | 12:56:43 | JRC RICE 5G | 183 | ~9s | **否** | — | `Probe failed` → `-IS_VALIDATED`，触发切换 |
| 2 | 12:56:53 | SHOAI2025_2.4G | 184 | 18.8s | **是** | 12:57:02 (+9.0s) | 此前 unvalidated×6，感叹号约 9s |
| 3 | 12:57:15 | JRC RICE 5G | 185 | 48.3s | **是** | 12:57:36 (+20.3s) | 验证最慢；期间多次 `Probe: not validated` |
| 4 | 12:58:04 | SHOAI2025_2.4G | 186 | **5.2s** | **否** | — | 仅 `+TRANSPORT_PRIMARY`，未等到 EVER_EVALUATED 即被切走 |
| 5 | 12:58:13 | JRC RICE 5G | 187 | **5.9s** | **否** | — | unvalidated×2 后断线 |
| 6 | 12:58:23 | SHOAI2025_2.4G | 188 | 14.1s | **是** | 12:58:31 (+8.2s) | — |
| 7 | 12:58:42 | JRC RICE 5G | 189 | 5.5s | **是** | 12:58:43 (+0.8s) | 验证很快，但 ~5s 后又被 SystemUI 切走 |
| 8 | 12:58:48 | SHOAI2025_2.4G | 190 | **5.6s** | **否** | — | 在线过短，未完成 EVER_EVALUATED |
| 9 | 12:58:54 | JRC RICE 5G | 191 | 6.2s | **是** | 12:58:55 (+1.2s) | — |
| 10 | 12:59:06 | JRC RICE 5G | 192 | 持续 | **是** | 12:59:07 (+0.8s) | 最终稳定连接 |

**汇总**：

| 指标 | 数值 |
|------|------|
| 总会话数 | 10 |
| 探测有网成功（断线前 EVER_EVALUATED） | **6 次** |
| 探测未完成/失败 | **4 次**（net 183 / 186 / 187 / 190） |
| 失败共同特征 | 关联后 **<6s** 即被 `WifiService: connect`（SystemUI）切到另一 SSID |
| 成功时典型验证耗时 | **0.8s ~ 20.3s** |

**机理补充**：每次 CONNECT 后框架均会启动互联网探测（`+TRANSPORT_PRIMARY` → Probe gstatic / 网关 Ping），但 SSID 乒乓导致多次短连接在验证完成前被打断，用户在此期间持续看到 **感叹号/无网感**——这与「信号很强但 WiFi 像丢了」的用户描述高度吻合。

### 阶段 4：恢复稳定（12:58:55 — 13:00:05）

| 时间 | 事件 |
|------|------|
| **12:58:55** | `Wifi network validated`，`mValidated=true`，network ID **191** |
| **12:58:55.507** | `ConnectivityService: net 191 : +EVER_VALIDATED+IS_VALIDATED` → **感叹号消失** |
| **12:59:07** | 再次 validated，network ID **192** |
| **12:59:17** | `MSG_FIRST_CONNECTED_VALIDATED` |
| **13:00:05** | `TranWifiSmartAssistant` 监测 **JRC RICE 5G**，RSSI 正常 — **与粉丝申报时刻一致，此时已无断连** |

---

## 【失败原因分类】

| 类别 | 判定 | 说明 |
|------|------|------|
| A. 弱信号 / 射频差 | ❌ 排除 | RSSI -40~-52，链路 3.9Gbps 协商 |
| B. AP 踢线 (deauth) | ❌ 排除 | 全部 `reason=3 locally_generated` |
| C. **Probe 误判 no-internet** | ✅ **主因** | gstatic.com ConnectException |
| D. **TranWifiSmartAssistant 自动切网** | ✅ **放大器** | 触发 SSID 乒乓，9 次 network lost |
| D2. **短连接打断探测** | ✅ **用户感知直接原因** | 4 次关联 <6s 未完成 EVER_EVALUATED，感叹号持续 |
| E. 驱动漫游故障 | ❌ 排除 | 为框架层 SSID 切换，非 RCPI 漫游 |
| F. 13:00 仍在断连 | ❌ 排除 | 13:00:05 日志显示已稳定 validated |

---

## 【关键日志】

### 1. Probe 失败（根因起点）

```
06-18 12:56:42.537 E WifiStat:NetworkProbe: Probe failed
06-18 12:56:42.537 E WifiStat:NetworkProbe: java.net.ConnectException: Failed to connect to connectivitycheck.gstatic.com/142.250.207.35:443
06-18 12:56:43.700 I WifiStatistics:WifiNetworkCheck: Wifi network unvalidated
06-18 12:56:43.745 I WifiClientModeImpl: Temporarily disabling network because of no-internet access
```

### 2. 自动选网触发切换

```
06-18 12:56:49.883 I WifiNetworkQuality: total score : JRC RICE 5G 3540
06-18 12:56:49.883 I WifiNetworkQuality: total score : SHOAI2025_2.4G 3622
06-18 12:56:49.883 I TranWifiSmartAssistantController: candidate is : "SHOAI2025_2.4G"
06-18 12:56:49.883 I TranWifiSmartAssistantController: current ssid:"JRC RICE 5G"in blacklist :true
```

### 3. 网络验证状态（ConnectivityService — 感叹号）

> **日志解读**：`ConnectivityService: Update score for net <id> : <标记>` 行末含 **`+EVER_EVALUATED`**（或 `+IS_VALIDATED`）= 已验证可上网；**`-IS_VALIDATED`** 或尚无 EVER_EVALUATED = 不可上网，**状态栏感叹号**。

```
06-18 12:56:43.684 I ConnectivityService: Update score for net 183 : -IS_VALIDATED
06-18 12:57:02.051 I ConnectivityService: Update score for net 184 : +EVER_EVALUATED
06-18 12:58:55.507 I ConnectivityService: Update score for net 191 : +EVER_VALIDATED+IS_VALIDATED
```

### 4. 连接发起方（WifiService）

> **日志解读**：`WifiService: connect uid=` 表示一次 WiFi 连接请求；`packageNameToUse=` 后为发起方包名。`com.android.systemui` = **SystemUI/系统框架代发**，通常对应自动选网、设置页或连通性恢复触发的连接，**不等于用户自己在 WiFi 列表里手动点击连接**。

```
06-18 12:56:52.669 I WifiService: connect uid=10144 packageNameToUse=com.android.systemui
06-18 12:58:04.199 I WifiService: connect uid=10144 packageNameToUse=com.android.systemui
06-18 12:58:09.582 I WifiService: connect uid=10144 packageNameToUse=com.android.systemui
```

### 5. 本机断连 + SSID 切换

```
06-18 12:56:52.736 I wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=c8:5a:9f:ba:ab:b1 reason=3 locally_generated=1
06-18 12:56:52.840 I wpa_supplicant: Trying to associate with SSID 'SHOAI2025_2.4G'
06-18 12:56:53.015 I wpa_supplicant: CTRL-EVENT-CONNECTED - Connection to f8:64:b8:ef:d5:2b completed
06-18 12:56:53.044 I WifiStatistics:WifiNetworkCheck: Wifi network lost
```

### 6. kernel 侧确认（本机主动断连）

```
[wlan] kalIndicateStatusAndComplete: Indicate disconnection: Reason=3 Locally[1]
[wlan] aisFsmDisconnectedAction: DISCONN_DONE bidx=0 ssid=*** bssid=c8:5a:**:**:**:b1
[wlan] authSendDeauthFrame: Reason=3 (本机发出 Deauth)
```

### 7. 申报时刻已恢复（13:00:05）

```
06-18 13:00:05.786 I TranWifiSmartAssistantController: mCurrentNetwork :192 SSID :"JRC RICE 5G"
```

---

## 【建议措施】

### WiFi / 框架层

1. **TranWifiSmartAssistant 优化**：用户手动选定的 SSID（`auto switch:false`）在 Probe 短暂失败时，**不应立即切换到其他已保存网络**，避免 SSID 乒乓。
2. **Probe 策略**：`connectivitycheck.gstatic.com` 在菲律宾部分运营商/AP 可能被阻断；建议增加 **fallback 探测目标** 或结合 **网关 Ping + DNS** 综合判定，降低误判 no-internet。
3. **no-internet 禁用逻辑**：强 RSSI + 网关 Ping 成功（12:56:47 Ping 260ms 仍 success）时，**延迟或放宽** `Temporarily disabling network`。
4. **短连接保护**：关联后 **<10s** 内若未完成 EVER_EVALUATED，**禁止再次自动切 SSID**，避免打断进行中的互联网探测。
5. **黑名单逻辑复核**：JRC RICE 5G 已在 blacklist 却仍被反复连回，需检查 blacklist 与 auto-reconnect 交互。

### 测试 / 粉丝侧

1. 确认 AP **JRC RICE 5G** 是否能正常访问 `connectivitycheck.gstatic.com`（浏览器或 curl 测试）。
2. 若不需要 **SHOAI2025_2.4G**，建议忘记该网络，减少自动切网候选。
3. 复现时抓取 **tcpdump** + 确认问题发生精确时刻（本次申报 13:00:05 时日志已无断连）。

### 工单流转

| 责任域 | 建议 |
|--------|------|
| **WiFi 框架** | 主查：Probe 误判 + SmartAssistant 切网策略（**高优先级**） |
| **AP/网络环境** | 辅查：gstatic 连通性、DNS 劫持 |
| **驱动** | 本次无需转 MTK driver（断连为本机发起） |

---

## 【附件】

- 工单元数据：`TOS163-37795.json`
- 日志目录：`AI-result/issues/TOS163-37795/logs/`
- 录屏：`Screen_Recording_20260618_125752.mp4`（OSS，未本地分析）

---

*报告由 WiFi Doctor 自动生成 | 分析模型：Claude*
