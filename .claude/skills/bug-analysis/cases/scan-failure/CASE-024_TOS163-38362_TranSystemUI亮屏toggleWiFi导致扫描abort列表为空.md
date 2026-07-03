# CASE-024: TranSystemUI 亮屏异常 toggle WiFi 导致扫描 abort — WiFi 列表为空

## 基本信息
- **案例ID**: CASE-024
- **分类**: scan-failure
- **来源**: TOS163-38362
- **创建时间**: 2026-06-08
- **匹配次数**: 0
- **MTK Case**: 143351909（MTK 确认驱动行为正常，责任在 TranSystemUI）

## 现象描述
- 巴基斯坦粉丝反馈：No Wifi Shows in the WiFi area having multiple Wifi Networks other phones show the wifi at the same place（高概率）
- 机型 TECNO CN6c（XYZ），Android 16 / HiOS 16.3.0（CN6c-16.3.0.126SP02 FANS），MTK 平台
- 申报时刻 **12:48:28**（Asia/Karachi）；周围多 AP 可见，本机 WiFi 设置列表 **完全为空**
- 粉丝恢复方式：**after restart the phone**（重启后正常）

## 根因结论

**非 WiFi 射频/固件扫不到热点。亮屏后 TranSystemUI `TrAirplaneModeTile` 异常触发 `setWifiEnabled(false→true)`，扫描在完成前被 abort（reason=-7），Kernel/Framework 扫描结果始终 0 AP，列表无法显示。**

机理链条：
1. **12:45:14** `policy_scene_name=wakefulness-changed`（设备亮屏）
2. **12:45:22** `Tile.TrAirplaneModeTile: handleRefreshState: airplane, mState.state=1`
3. **12:45:23** `WifiService: setWifiEnabled package=com.android.systemui enable=false`
4. Kernel `wlanStop abort scan!` → `Scan Abort` → `Reason:DRIVER ABORT` → `0 Bss is found`
5. **12:45:25** `setWifiEnabled enable=true`
6. **12:45:55 / 12:47:53** `WifiScanRequestProxy: Scan failure received. reason: -7, description: Scan aborted`
7. **12:48:01** 用户打开 WiFi 设置，`WifiPickerTracker: Scanning started`，但 `ScanResult` 仍为空
8. 重启手机后系统状态复位，扫描恢复

**初判纠正**：Kernel `0 Bss` / `ucCompleteChanCount[0]` 不代表空口无 AP，而是 **scan 被 abort 或未完成**。

## 问题窗口统计

| 指标 | 数值 |
|------|------|
| Kernel `0 Bss is found` | 13 次（kernel_log_8） |
| `wlanStop abort scan!` | ≥1 次 |
| Framework `Scan failure -7` | 2 次 |
| SystemUI `setWifiEnabled false` | 1 次（12:45:23） |

## 排查步骤

1. **排除射频无 AP**：用户描述及其他手机可见多 AP；问题是 **列表为空** 非单 AP 弱
2. **查 WiFi toggle 来源**：`setWifiEnabled` 的 `package=` 是否为 `com.android.systemui` / TranSystemUI
3. **查亮屏关联**：toggle 前是否有 `wakefulness-changed`、`TrAirplaneModeTile handleRefreshState`
4. **查扫描 abort**：`Scan failure reason: -7 Scan aborted` + kernel `wlanStop abort scan` / `DRIVER ABORT`
5. **查 0 Bss 含义**：`ucCompleteChanCount[0]`、`u4ScanDurBcnCnt[0]` = 扫描未完成任何信道
6. **勿误判 MTK 固件**：WiFi OFF 时 abort scan 为驱动预期；根因在 **谁触发了 OFF**
7. **验证恢复方式**：重启是否恢复 → 支持状态机未自恢复结论

## 关键日志

```
// 亮屏 + Tile 刷新
06-23 12:45:14.259  policy_scene_name=wakefulness-changed
06-23 12:45:22.758  Tile.TrAirplaneModeTile: handleRefreshState: airplane, mState.state=1

// SystemUI 异常 toggle
06-23 12:45:23.660  WifiService: setWifiEnabled package=com.android.systemui enable=false
06-23 12:45:25.441  WifiService: setWifiEnabled package=com.android.systemui enable=true

// Framework 扫描 abort
06-23 12:45:55.886  WifiScanRequestProxy: Scan failure received. reason: -7, description: Scan aborted
06-23 12:47:53.024  WifiScanRequestProxy: Scan failure received. reason: -7, description: Scan aborted

// 列表仍空
06-23 12:48:01.586  WifiPickerTracker: Scanning started
06-23 12:48:01.585  ScanResultUtil: Empty or null ScanResult list

// Kernel
wlanStop:(INIT DEBUG) wlanStop abort scan!
SCANLOG: [SCN:1200:D2F] Scan Abort#193 to Q: isExtCh=0
SCANLOG: [SCN:600:D2K] 0 Bss is found, 0, 0, 0, 0
Send UEvent: Scan=Status:ABNORMAL, Reason:DRIVER ABORT
```

## TAG
- scan-failure
- 扫描失败
- Scan aborted
- reason=-7
- 0 Bss
- Empty ScanResult
- WiFi列表为空
- TranSystemUI
- TrAirplaneModeTile
- wakefulness-changed
- 亮屏
- setWifiEnabled
- SystemUI副作用
- wlanStop abort scan
- DRIVER ABORT
- ucCompleteChanCount0
- 重启恢复
- CN6c
- 巴基斯坦
- MTK driver
- 粉丝反馈

## 建议措施

### TranSystemUI（优先）
1. 审查 `TrAirplaneModeTile.handleRefreshState()`：亮屏时 **禁止误调 `setWifiEnabled(false)`**
2. 核对 `mState.state` 与 `airplane_mode_on` 系统属性是否一致
3. toggle 后 scan 连续失败时增加 **自动恢复扫描**

### 验证
4. 亮屏复现：无 SystemUI `setWifiEnabled false`；Kernel `Total:x/y` > 0
5. MTK Case 可关闭（驱动侧无异常）

### 用户侧
6. 列表空白可 **重启手机** 临时恢复

## 关联案例
- **CASE-018**（高匹配）：Transsion 组件 `setWifiEnabled(false)` 副作用导致断网
- **CASE-012**（弱相关）：`ScanResult` 空 + `WifiNetworkQuality` 问题

## 分析报告
- `AI-result/issues/TOS163-38362/TOS163-38362-analysis.md`
- 本地日志：`AI-result/issues/TOS163-38362/logs/`
