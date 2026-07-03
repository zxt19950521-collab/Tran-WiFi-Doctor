# CASE-023: RADIO_LOST 断连后扫描未命中 saved 网络 — Framework 不重连导致 WiFi 连接慢

## 基本信息
- **案例ID**: CASE-023
- **分类**: disconnect
- **来源**: CN6OS16-2071
- **创建时间**: 2026-06-08
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝反馈：sometimes it takes a minute to connect at the WiFi（偶现 WiFi 连接慢）
- 机型 TECNO CN6（XYZ），Android 16 / HiOS 16.3.0（CN6-16.3.0.130 FANS），MTK 平台
- 申报时刻 **18:46:53**（Asia/Manila）；连接 SSID **♡HQWayyyfayyy♡**（5GHz ch132，BSSID `58:ae:f1:ca:18:18`）
- 游戏场景（Roblox 前台）；密集邻区 WiFi（kernel 扫描 20—64 AP）
- 截图 18:46:09：Quick Settings Wi-Fi On 但未显示已连接 SSID

## 根因结论

**非关联/DHCP 慢，而是「链路恶化 RADIO_LOST 断连 → 扫描多次但未命中 saved SSID → Framework 108s 未自动重连 → 用户 toggle WiFi 叠加 24s 重扫」；L2 关联本身仅 ~55ms。**

机理链条：
1. **18:43:37—18:44:05** 游戏大流量下 PER **94%**、RSSI **-93~-95**，驱动漫游 POOR_RCPI/TX_ERR 多次 FAIL
2. **18:44:05** `Trigger BTO disconnection` → `RADIO_LOST` → `CTRL-EVENT-DISCONNECTED reason=10003`（非用户主动）
3. **18:44:05—18:45:53** `WifiClientModeImpl: disconnectedstate` 驻留 **~108s**，无 `Trying to associate`
4. **18:44:08** `mValidSavedNetworks={}` → `TranWifiSmartAssistantController: candidate is null!`（Framework 仅 5 个有效 AP，目标 SSID 不在列表）
5. Kernel 断连后 **≥3 次** `mtk_cfg80211_scan` 全扫（24/29、18/21、22/26 AP），但 **HQWayyyfayyy 均缺席**（不是「没扫」）
6. **18:45:53** 用户 SystemUI `setWifiEnabled false→true` → supplicant Terminate → **~24s** 后扫到 SSID 才连上
7. **18:46:17.886** CONNECTED（assoc ~55ms）→ **18:46:18** VALIDATED

总等待断连→可用 **~2m12s**，与用户「about a minute」体感一致。

## 耗时分解（核心判据）

| 阶段 | 时长 | 说明 |
|------|------|------|
| 断连 → 用户关 WiFi | ~108s | Framework 未重连 |
| WiFi OFF→ON + 重扫 | ~24s | supplicant 全重启 |
| 关联 + VALIDATED | ~1s | 非瓶颈 |

## 排查步骤

1. **排除关联慢**：查 `Trying to associate` → `CTRL-EVENT-CONNECTED` 间隔（本案 ~55ms）
2. **排除 DHCP 慢**：查 `+VALIDATED` 是否在 CONNECTED 后 1s 内（本案 ~0.5s）
3. **查断连原因**：`reason=10003` + kernel `RADIO_LOST` / `Trigger BTO disconnection`；对比 `locally_generated`
4. **查 disconnectedstate 驻留**：断连后是否有 `Trying to associate` / `CMD_START_CONNECT`
5. **查 saved-network 匹配**：`mValidSavedNetworks` 是否为空、`candidate is null`
6. **查 Kernel 扫描**（勿误判为没扫）：`mtk_cfg80211_scan`、`SCANLOG Total:x/y`、目标 SSID 是否间歇缺席
7. **区分 CASE-019**：本案 `candidate is null` **未切网也未重连**；CASE-019 为 Probe 失败 SSID 乒乓

## 关键日志

```
// 断连
06-24 18:44:05.420  wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=58:ae:f1:ca:18:18 reason=10003
06-24 18:44:05.477  WifiClientModeImpl: disconnectedstate enter

// 未自动重连
06-24 18:44:08.391  WifiNetworkQuality: mValidSavedNetworks is :{}
06-24 18:44:08.391  TranWifiSmartAssistantController: candidate is null!

// Kernel 断连机理
06-24 10:44:05.410  aisSearchHandleBadBssDesc: Trigger BTO disconnection
06-24 10:44:05.411  kalIndicateStatusAndComplete: Indicate disconnection: Reason=10003 Locally[0]

// Kernel 扫描有触发但无目标 SSID
06-24 10:44:08.378  SCANLOG: [SCN:600:D2K] Total:24/29  ...（无 HQWayyyfayyy）
06-24 10:46:17.664  SCANLOG: [SCN:600:D2K] Total:11/13  ...♡HQWayyyfayyy♡...

// 用户 toggle + 快速关联
06-24 18:45:53.328  WifiService: setWifiEnabled ... enable=false
06-24 18:45:53.824  WifiService: setWifiEnabled ... enable=true
06-24 18:46:17.830  wpa_supplicant: Trying to associate with SSID '♡HQWayyyfayyy♡'
06-24 18:46:17.886  wpa_supplicant: CTRL-EVENT-CONNECTED
06-24 18:46:18.431  ConnectivityService: +VALIDATED
```

## TAG
- slow-connect
- 连接慢
- RADIO_LOST
- reason=10003
- BTO disconnection
- TX_ERR漫游
- PER高
- 漫游失败
- disconnectedstate
- 未自动重连
- candidate is null
- mValidSavedNetworks空
- 扫描未命中
- scan-miss
- dense-ap
- TranWifiSmartAssistant
- setWifiEnabled
- Roblox
- CN6
- 菲律宾
- MTK driver
- 粉丝反馈

## 建议措施

### WiFi 框架（优先）
1. `disconnectedstate` 驻留超阈值（15—30s）且 WiFi enabled 时，**强制 saved-network 定向重扫/按 BSSID 重试**
2. `candidate is null` 时回落 **AOSP WifiConnectivityManager 默认重连**，勿静默等待
3. 审查 TX_ERR 场景下 **BTO disconnection** 阈值是否过于激进

### 用户侧
4. 断连后勿立即 OFF→ON WiFi（会触发 supplicant 全重启）；优先等待或手动点选 SSID

## 关联案例
- **CASE-006**（弱相关）：弱信号 PER 高漫游失败
- **CASE-013**（弱相关）：漫游 churn 导致卡顿
- **CASE-019**（对比）：Probe 失败 SSID 乒乓；本案为 **断连后不重连**
- **CASE-018**（弱相关）：SystemUI `setWifiEnabled` 副作用

## 分析报告
- `AI-result/issues/CN6OS16-2071/CN6OS16-2071-analysis.md`
- 本地日志：`AI-result/issues/CN6OS16-2071/logs/`
