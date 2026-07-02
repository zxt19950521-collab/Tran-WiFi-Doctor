# CASE-030: SystemUI 状态栏 WiFi 图标隐藏 — WiFi 已 validated 但用户误判需多次连接

## 基本信息
- **案例ID**: CASE-030
- **分类**: disconnect
- **来源**: TOS163-40301
- **创建时间**: 2026-06-08
- **匹配次数**: 0

## 现象描述
- 孟加拉国粉丝反馈：WiFi network does not get connected at first try, have to attempt multiple times for connecting（偶现一次）
- 机型 TECNO CN6c，Android 16 / HiOS 16.3.0（CN6c-16.3.0.130SP02 FANS），MTK 平台
- 家庭 WiFi **Wifi nai**（2.4G ch6，BSSID `50:d2:f5:b8:ee:8b`）
- 录屏（~18:55:35）：状态栏仅显示蜂窝 **4.5G**、**无 WiFi 图标**；QS 显示 Connecting...；Settings Toast **Connection failure**；最终 Settings 显示 Connected 但状态栏仍无 WiFi 图标

## 根因结论

**非 WiFi 框架多次 assoc 失败。WiFi 底层单次 assoc 即成功且长时 validated；用户「需多次尝试」源于 SystemUI 隐藏 WiFi 图标 + Settings/QS UI 层 Connection failure，误判未连接而反复手动连接。**

机理链条：
1. **18:27:35~38** 用户打开 WiFi → **唯一一次** `Trying to associate` → L2 ~1.2s CONNECTED → **18:27:38 validated**
2. **18:27:44** `SCREEN_OFF` → `TrCollapsedStatusBarFragment: endSideContentAlpha:0.0, mSystemIconsView visibility:0`（WiFi 图标区 GONE）
3. **18:27:45** `ModernStatusBarWifiView visibleState=ICON` 但父容器已隐藏 → 图标逻辑应显示、UI 不可见
4. **18:33:24 ~ 18:56+** `endSideContentAlpha` 始终 0.0，录屏窗口内未恢复；Keyguard 解锁后仍 0.0
5. 蜂窝 **4.5G**（LTE-A）走 `MobileIconViewModel` / `KeyguardStatusBarView` 独立路径仍可见；`mobileIsDefault: false`（WiFi 为默认网络）
6. 录屏 ~13s **Connection failure**：无第 2 次 assoc、无 wpa disconnect、无 `setWifiEnabled` — **UI 层误报**

## 问题窗口统计

| 指标 | 数值 |
|------|------|
| `Trying to associate`（全日志） | **1 次**（成功） |
| ASSOC_REJECT / auth failure | **0** |
| WiFi 断连 / network lost（18:27 后） | **0** |
| validated（18:27:38 后） | **持续** |
| 录屏 Connection failure 对应 L2 失败 | **0** |
| `endSideContentAlpha=1.0`（18:33 后） | **0 次** |

## 录屏 UI 时间轴（映射日志 ~18:55:35）

| 录屏时间 | UI 表现 | 框架层 |
|----------|---------|--------|
| 0s | 4.5G，无 WiFi 图标 | validated；mobileIsDefault=false |
| 10s | QS Wifi nai — Connecting... | 无新 assoc；已 L2 连接 |
| ~13s | Connection failure Toast | 无 assoc 失败 |
| 25s | Settings Connected，状态栏仍无 WiFi 图标 | validated；图标区仍 GONE |

## 排查步骤

1. **统计 assoc 次数**：`Trying to associate` 是否仅 1 次且成功；勿仅凭用户描述定多次 assoc 失败
2. **对齐 validated**：`ConnectivityService: +VALIDATED`、`Wifi network validated` 是否持续
3. **查 SystemUI 图标可见性**：`TrCollapsedStatusBarFragment` + `endSideContentAlpha` + `mSystemIconsView visibility`
4. **对比 WiFi 图标状态 vs 父容器**：`ModernStatusBarWifiView visibleState=ICON` 时父容器是否 GONE
5. **查 SCREEN_OFF/AOD/解锁路径**：亮屏/Keyguard GONE 后 `endSideContentAlpha` 是否恢复 1.0
6. **录屏对齐 Connection failure**：Toast 时刻是否有 wpa disconnect / 第 2 次 assoc
7. **区分 4.5G**：状态栏 4.5G = 蜂窝 LTE-A，非 WiFi；查 `mobileIsDefault` 确认默认网络
8. **排除蜂窝抢默认网**：本案 `mobileIsDefault: false`，WiFi 为 default network

## 关键日志

```
// 单次 assoc 成功
06-26 18:27:35  WifiService: setWifiEnabled enable=true (SystemUI)
06-26 18:27:36  wpa_supplicant: Trying to associate with SSID 'Wifi nai'
06-26 18:27:36  wpa_supplicant: CTRL-EVENT-CONNECTED completed
06-26 18:27:38  ConnectivityService: +VALIDATED

// SCREEN_OFF 隐藏图标区
06-26 18:27:44  action=android.intent.action.SCREEN_OFF
06-26 18:27:44  TrCollapsedStatusBarFragment: endSideContentAlpha:0.0, mSystemIconsView visibility:0
06-26 18:27:45  ModernStatusBarWifiView visibleState=ICON

// 录屏窗口：框架已连、UI 无图标
06-26 18:55:36  WifiStatistics:WifiNetworkCheck: Wifi network validated
06-26 18:55:37  NearbyMediums: isWifiConnected=true
06-26 18:55:39  MobileIconViewModel: mobileIsDefault: false
06-26 18:55:39  TrCollapsedStatusBarFragment: endSideContentAlpha:0.0, mSystemIconsView visibility:0
```

## TAG
- SystemUI状态栏
- WiFi图标隐藏
- endSideContentAlpha
- TrCollapsedStatusBarFragment
- mSystemIconsView
- ModernStatusBarWifiView
- SCREEN_OFF
- UI层ConnectionFailure
- 日志未复现多次assoc
- 单次assoc成功
- validated
- mobileIsDefault
- 4.5G蜂窝
- TranSystemUI
- CN6c
- 孟加拉国
- 粉丝反馈
- MTK平台

## 建议措施

### SystemUI（优先）
1. 排查 `TrCollapsedStatusBarFragment.updateStatusBarVisibilities()`：`SCREEN_OFF` / AOD / Keyguard 解锁后 **`endSideContentAlpha` 未恢复 1.0**
2. 关注 `SplitQsStatusBarController` 与 collapsed status bar 交互

### Settings/WiFi UI
3. 已 L2 连接且 validated 时，手动 connect 应 refresh 状态，不应 Toast **Connection failure**

### 验证
4. 复现指标：Settings Connected 但状态栏无 WiFi 图标即本模式
5. WiFi 框架/驱动：本案证据不足，勿按 assoc 失败排查

## 关联案例
- **CASE-024**（高相关）：TranSystemUI 亮屏异常导致 WiFi 侧问题（扫描 abort vs 本案图标隐藏）
- **CASE-012**（部分相似）：系统 WiFi 正常但用户/App 层误判未连接
- **CASE-019**（弱相关）：SystemUI 发起 connect + 状态栏异常显示

## 分析报告
- `AI-result/issues/TOS163-40301/TOS163-40301-analysis.md`
- 本地日志/录屏：`AI-result/issues/TOS163-40301/logs/`
