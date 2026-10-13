# CASE-040: 产线 RF 工位残留 FTM 模式导致 *#802# WiFi2.4G/5G 测试扫描失败

## 基本信息
- **案例ID**: CASE-040
- **分类**: scan-failure
- **来源**: X6766OS17-879
- **创建时间**: 2026-10-13
- **匹配次数**: 0
- **平台**: 高通 WCN6450（qca_cld3_wcn6450 v5.2.1.96X）

## 现象描述
- 产线 X6766 PR1-1，版本 X6766-17.0.0.035SP02(BASE003PF001AZ)SMT3
- 工模 *#802# 测试中，WiFi2.4G 和 WiFi5G **第一次测试均 NG**（10 s 超时），**重启后复测 PASS**
- 工单标注为偶现，重启后恢复

## 根因结论

**这不是射频或驱动功能缺陷，而是产线工序问题。WiFi RF 测试工位用 `insmod qca_cld3_wcn6450.ko con_mode=5` 把驱动切到 FTM 模式，结束后既没有恢复 con_mode=0，也没有重启。驱动因此残留在 FTM 模式，拒绝所有正常模式的 scan 和 vendor 命令，802 扫描超时 NG。**

机理链条：
1. **09-24 18:27:54** PC 端经 adb 依次执行 `svc wifi disable` → `svc bluetooth disable` → `adb root`
2. **18:27:57** 执行 `rmmod qca_cld3_wcn6450.ko`，日志显示 `Hard Unloading driver`
3. **18:27:58** 执行 `insmod /vendor/lib/modules/qca_cld3_wcn6450.ko con_mode=5`，kernel 打印 `hdd_wlan_start_modules: in ftm mode`
4. **18:28:01** 执行 `ifconfig wlan0 up` → `ftmdaemon -n -dd`（RF 测试）
5. **18:29:08** USB 断开。之后没有执行 con_mode=0，也没有 reboot，手机连续开机 14 天
6. **10-08 19:01** 进入 *#802#，执行 `setWifiEnabled(true)` 后，HAL 打印 `Error -1`，并出现 `WificondScannerImpl: Failed to start scan`
7. kernel 打印 `__wlan_hdd_cfg80211_scan: Command not allowed in FTM mode`，App 中 `resultUpdated=false`，10 s 后判 NG
8. **19:14:58** 重启后驱动按默认 con_mode=0 加载，19:18 复测时 2.4G 和 5G 均 PASS

## 问题窗口统计

| 指标 | 数值 |
|------|------|
| 重启前 802 WiFi 测试 | 3 项次，全部 NG（首测 2.4G、首测 5G、单项复测 2.4G） |
| 重启后 802 WiFi 测试 | 2 项次，全部 PASS |
| kernel `Command not allowed in FTM mode`（10-08） | 200 条 |
| 重启后 kernel 中 FTM 字样 | 0 条 |
| 驱动处于 FTM 模式的时长 | 约 14 天（09-24 18:27 → 10-08 19:14） |

## 排查步骤

1. **工模 App**：查看 `tf/m_WifiLogic` 是否为 `onTestTimeout`，以及 `tf/m_Wifi: onReceive: resultUpdated = false`；判定条件是 `band / timeout=10000 / passCount=1 / levelMin=-70`
2. **Framework/HAL**：查找 `WificondScannerImpl: Failed to start scan`，以及 WifiHAL 大面积出现的 `acquire_supported_features ... Error:-1` 和 `wifi_get_firmware_version: Error -1`
3. **Kernel**：grep `Command not allowed in FTM mode`，命中即可确认驱动处于 FTM 模式
4. **回溯来源**：在 kernel 中找最早的 `in ftm mode` 和 `Loading driver`；在 main log 中 grep `adbd service requested`，找到 `insmod ... con_mode=5` 以及发起它的工位脚本
5. **确认未重启**：对比 `stability/` 或 `pmic_pon/` 下的启动时间点，确认 FTM 切换之后、802 测试之前没有重启
6. **排除项**：没有 SSR 或 recovery 记录（`is_driver_recovering 0`）；重启后同一环境立即 PASS，可以排除射频和天线问题

## 关键日志

```
// RF 工位切 FTM（mainlogcat-log.I01 / kernellogcat-log.I01）
09-24 18:27:57.724982 adbd: adbd service requested '...raw:rmmod qca_cld3_wcn6450.ko'
09-24 18:27:58.040317 adbd: adbd service requested '...raw:insmod /vendor/lib/modules/qca_cld3_wcn6450.ko con_mode=5'
09-24 18:27:58.720766 wcn6450: [HDD] hdd_wlan_start_modules: in ftm mode, no need to configure cds modules
09-24 18:28:01.254030 adbd: adbd service requested '...raw:ftmdaemon -n -dd'
09-24 18:29:08.104703 adbd: UsbFfs: connection terminated

// 802 测试失败
10-08 19:01:12.980162 WifiHAL : acquire_supported_features: requestResponse Error:-1
10-08 19:01:13.103101 WificondScannerImpl: Failed to start scan, freqs={2412, ... 5180, ...}
10-08 19:01:19.226862 wcn6450: [HDD] __wlan_hdd_cfg80211_scan: Command not allowed in FTM mode
10-08 19:01:22.938553 tf/m_WifiLogic/BaseLogic: onTestTimeout: WiFi2.4G timeout 10000ms
10-08 19:13:12.609210 tf/m_Wifi: onReceive: resultUpdated = false

// 重启后 PASS
10-08 19:18:48.065062 tf/m_WifiLogic/BaseLogic: setResult: itemName = WiFi2.4G, pass = true
10-08 19:18:51.625432 tf/m_WifiLogic/BaseLogic: setResult: itemName = WiFi5G, pass = true
```

## TAG
- scan-failure
- 扫描失败
- WificondScannerImpl失败
- 驱动FTM模式残留
- Command not allowed in FTM mode
- con_mode=5
- ftmdaemon
- 产线工序
- *#802#
- 工模MMI
- tranfacmode
- 重启恢复
- 2.4G频段
- 5G频段
- X6766
- WCN6450
- 高通平台

## 建议措施

### 产线工艺（优先）
1. RF/FTM 工位脚本结束时必须恢复正常模式：执行 `adb reboot`（推荐），或执行 `rmmod` 后再 `insmod ... con_mode=0`，并确认 `/sys/module/qca_cld3_wcn6450/parameters/con_mode` 为 0
2. 排查同工位、同脚本处理过的其他机台

### 工模 App 防呆
3. WifiLogic 启动前读取 con_mode。如果不为 0，直接提示“WLAN 处于 FTM 模式，请重启”，避免误判为硬件不良

### 用户侧 / 产线临时规避
4. 802 WiFi NG 时先重启整机再复测

## 关联案例
- **CASE-024**（弱相关）：同样是扫描失败、重启恢复，但根因是 TranSystemUI 误 toggle WiFi 导致 scan abort，不是驱动模式问题

## 分析报告
- `AI-result/issues/X6766OS17-879/X6766OS17-879-analysis.md`
- 本地日志：`AI-result/issues/X6766OS17-879/logs/W000286/`
