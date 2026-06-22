# CASE-019: Probe 失败触发 SmartAssistant SSID 乒乓 — 强信号下 network lost / 状态栏感叹号

## 基本信息
- **案例ID**: CASE-019
- **分类**: disconnect
- **来源**: TOS163-37795
- **创建时间**: 2026-06-22
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝反馈：WiFi 信号很强，但偶尔感觉 WiFi「丢失」（lost a wifi signal while the wifi connect is very strong）
- 机型 TECNO CN6（XYZ），Android 16 / HiOS 16.3.0（CN6-16.3.0.127 FANS），MTK 平台
- 偶现（occasional）；申报时刻 **13:00:05**（Asia/Manila），实际断连潮在 **12:56:42 — 12:59:06**
- 连接 **JRC RICE 5G**（5GHz ch52，BSSID `c8:5a:9f:ba:ab:b1`），RSSI **-44 ~ -52 dBm**，kernel 协商 **3900/4333 Mbps**
- 与已保存网络 **SHOAI2025_2.4G** 之间发生 **SSID 乒乓**（非 BSSID 漫游）

## 根因结论

**非弱信号掉线，而是「NetworkProbe 失败 → no-internet → TranWifiSmartAssistant 自动切网」引发的 SSID 乒乓；短连接在 EVER_EVALUATED 完成前被打断，状态栏持续感叹号。**

机理链条：
1. **12:56:42** `WifiStat:NetworkProbe` 连接 `connectivitycheck.gstatic.com` **ConnectException**
2. **12:56:43** `mValidated=false`、`-IS_VALIDATED`、`Temporarily disabling network because of no-internet access`
3. **TranWifiSmartAssistant** 评分：SHOAI2025_2.4G **3622** > JRC RICE 5G **3540** → SystemUI 发起切网（`WifiService: connect packageNameToUse=com.android.systemui`）
4. **12:56:53 — 12:59:00** 两 SSID 反复切换：**9 次 CONNECT / 9 次 network lost**，全部 `reason=3 locally_generated`（本机主动断连，非 AP deauth）
5. **10 段 WiFi 会话**中仅 **6 次**在断线前完成 `+EVER_EVALUATED`；**4 次**在线 **<6s** 未完成验证 → **状态栏感叹号持续**
6. **12:59:07** net 192 稳定 validated；申报 **13:00:05** 时已无断连

与用户描述一致：**物理层强信号**，但 L3 层多次 `network lost` + 感叹号，体感「WiFi 丢了」。

## 逐次连接后探测有网（核心证据）

| # | 连接时间 | SSID | net | 在线时长 | 探测有网 | EVER_EVALUATED |
|---|----------|------|-----|----------|----------|----------------|
| 1 | 12:56:43 | JRC RICE 5G | 183 | ~9s | 否 | —（Probe failed） |
| 2 | 12:56:53 | SHOAI2025_2.4G | 184 | 18.8s | 是 | 12:57:02 (+9.0s) |
| 3 | 12:57:15 | JRC RICE 5G | 185 | 48.3s | 是 | 12:57:36 (+20.3s) |
| 4 | 12:58:04 | SHOAI2025_2.4G | 186 | 5.2s | **否** | 未完成即被切走 |
| 5 | 12:58:13 | JRC RICE 5G | 187 | 5.9s | **否** | 未完成即被切走 |
| 6 | 12:58:23 | SHOAI2025_2.4G | 188 | 14.1s | 是 | 12:58:31 (+8.2s) |
| 7 | 12:58:42 | JRC RICE 5G | 189 | 5.5s | 是 | 12:58:43 (+0.8s) |
| 8 | 12:58:48 | SHOAI2025_2.4G | 190 | 5.6s | **否** | 未完成即被切走 |
| 9 | 12:58:54 | JRC RICE 5G | 191 | 6.2s | 是 | 12:58:55 (+1.2s) |
| 10 | 12:59:06 | JRC RICE 5G | 192 | 持续 | 是 | 12:59:07 (+0.8s) |

**判定规则**：
- `ConnectivityService: Update score for net <id> : +EVER_EVALUATED`（或 `+IS_VALIDATED`）→ 已验证可上网
- `-IS_VALIDATED` 或仅有 `+TRANSPORT_PRIMARY` 而无 EVER_EVALUATED → 不可上网，**状态栏感叹号**

## 排查步骤

1. **排除弱信号**：查 RSSI、kernel `link speed`，本案强信号 + 高协商速率
2. **查 Probe 失败**：`WifiStat:NetworkProbe: Probe failed` + gstatic ConnectException
3. **查 validated 失效**：`-IS_VALIDATED`、`no-internet access`、`Wifi network unvalidated`
4. **查自动切网**：`TranWifiSmartAssistant` + `WifiNetworkQuality` 评分 + `WifiService: connect packageNameToUse=com.android.systemui`
5. **查 SSID 乒乓**：`CTRL-EVENT-CONNECTED` / `DISCONNECTED reason=3 locally_generated` 是否在两个 SSID 间交替
6. **逐次验证**：每段 CONNECT 后是否出现 `+EVER_EVALUATED`；短连接（<6s）是否被打断
7. **区分漫游**：本案为 **SSID 切换**，非 `roamingFsmRunEventDiscovery` BSSID 漫游（对比 CASE-014）

## 关键日志

```
// 根因起点：Probe 失败
06-18 12:56:42.537 E WifiStat:NetworkProbe: Probe failed
06-18 12:56:42.537 E WifiStat:NetworkProbe: java.net.ConnectException: Failed to connect to connectivitycheck.gstatic.com/142.250.207.35:443
06-18 12:56:43.684 I ConnectivityService: Update score for net 183 : -IS_VALIDATED
06-18 12:56:43.745 I WifiClientModeImpl: Temporarily disabling network because of no-internet access

// SmartAssistant 自动选网
06-18 12:56:49.883 I WifiNetworkQuality: total score : JRC RICE 5G 3540
06-18 12:56:49.883 I WifiNetworkQuality: total score : SHOAI2025_2.4G 3622
06-18 12:56:52.669 I WifiService: connect uid=10144 packageNameToUse=com.android.systemui

// SSID 乒乓
06-18 12:56:52.736 I wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=c8:5a:9f:ba:ab:b1 reason=3 locally_generated=1
06-18 12:56:53.015 I wpa_supplicant: CTRL-EVENT-CONNECTED - Connection to f8:64:b8:ef:d5:2b completed
06-18 12:56:53.044 I WifiStatistics:WifiNetworkCheck: Wifi network lost
06-18 12:57:02.051 I ConnectivityService: Update score for net 184 : +EVER_EVALUATED

// kernel：本机主动断连
[wlan] kalIndicateStatusAndComplete: Indicate disconnection: Reason=3 Locally[1]

// 恢复
06-18 12:58:55.507 I ConnectivityService: Update score for net 191 : +EVER_VALIDATED+IS_VALIDATED
06-18 12:59:07.584 I ConnectivityService: Update score for net 192 : +EVER_EVALUATED
```

## TAG
- network lost
- 强信号
- Probe失败
- 网络验证失败
- 无互联网
- 网络未验证感叹号
- SystemUI发起连接
- TranWifiSmartAssistant
- SSID乒乓
- reason=3 locally_generated
- EVER_EVALUATED
- ConnectivityService
- CN6
- 菲律宾
- MTK driver
- 粉丝反馈

## 建议措施

### WiFi 框架（优先）
1. 用户手动选定 SSID（`auto switch:false`）时，Probe 短暂失败**不应立即切到其他已保存网络**
2. `connectivitycheck.gstatic.com` 不可达时增加 **fallback 探测**（网关 Ping + DNS）
3. 强 RSSI + 网关 Ping 成功时，**延迟或放宽** `Temporarily disabling network`
4. 关联后 **<10s** 内若未完成 EVER_EVALUATED，**禁止再次自动切 SSID**

### 测试 / 环境
5. 确认 AP 能否访问 gstatic；不需要的已保存 SSID 建议「忘记」
6. 复现抓 tcpdump + 精确对齐申报时刻

## 关联案例
- **CASE-012**（高匹配）：`NetworkProbe` 失败 → `network lost` / validated 问题
- **CASE-014**（弱相关）：驱动 BSSID 漫游导致 network lost；本案为 **框架 SSID 切换**

## 分析报告
- `reports/TOS163-37795-analysis.md`（完整分析报告）
- 本地日志：`AI-result/issues/TOS163-37795/logs/`
