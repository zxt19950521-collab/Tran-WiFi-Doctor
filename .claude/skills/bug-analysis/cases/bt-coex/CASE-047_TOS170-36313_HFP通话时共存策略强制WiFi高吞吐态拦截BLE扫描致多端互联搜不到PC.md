# CASE-047: HFP 通话时 BT/WiFi 共存策略强制 "WiFi 高吞吐" 态，拦截 BLE 扫描致多端互联搜不到 PC

## 基本信息
- **案例ID**: CASE-047
- **分类**: bt-coex
- **来源**: TOS170-36313
- **创建时间**: 2026-10-19
- **匹配次数**: 0

## 现象描述
- 【交付】【AIOT】【X6765】【PR0】【STR4】【多端互联】蓝牙通话过程中配对 PC，无法配对成功（Critical / must）
- 步骤：测试机后台蓝牙通话 → 多端互联搜索 Windows 电脑（TECNO-T15AA）并发起配对
- 结果：测试机搜不到电脑，无法配对；SCO 结束后扫描恢复
- 机型 X6765，MTK 平台；STA 连接 `QR123`（RSSI -44 ~ -60 dBm）
- kernel `.localtime` 为 UTC，需要 +8h 与 main log（Asia/Shanghai）对齐

## 根因结论

**WiFi 不是根因。BT 框架共存模块 `TranCoexMonitor` 在 HFP SCO 建立时以 `ignoreWifiMsg=true` / `persist=true` 强制 `wifi_state=1`（`wifi_ftp_On=true`），`BtScan.ScanManager.isCoexState()` 因此为 true，挂起并拒绝 `com.transsion.iotservice` 的 BLE 扫描。WiFi 实测吞吐量约 0.02 Mbps，kernel `lv:0`，并非高吞吐，"WiFi 高吞吐 + HFP" 这个双条件实际退化成了 "只要 HFP 就禁止扫描"。**

机理链条：
1. **10:34:04 ~ 10:34:07** 多端互联 P2P GC 加入 `DIRECT-M7-TCIRCLE`（5805 MHz），DHCP、Socket 正常，3.1s 后由 TCircle 页面主动断开（reason=3 locally_generated=1），与本问题无关
2. **10:34:09.633** P2P 断开 1.7s 后出现 `wifi_high_tput: 1`（同期 kernel 吞吐量 0.054 Mbps，上报方未打印）
3. **10:34:12.128** SCO AudioConnected → `ignoreWifiMsg: true` → `handleWifiTpOn persist=true, liveCoex=true, wifiTp=true` → `suspend ble scan`
4. **10:34:24.755** `isCoexState active, not support start scan for system app ScanClient(packageName=com.transsion.iotservice ...)`
5. **10:34:52.889** SCO 断开 → `resume ble scan`
6. **10:35:26.946** 第二次 SCO：此前 `wifi_state: 0`，没有任何 `wifi_high_tput` 上报，SCO 连上的同一毫秒变为 `wifi_state: 1 ... wifi_ftp_On: true` → 再次 `suspend ble scan`（**关键证据：共存态由 HFP 强制置位**）
7. **10:35:50.048** SCO 断开 → `resume ble scan`

## 设计要求符合性

设计要求（单位 KB/s，需求方确认）：停止扫描需同时满足 3.1 WiFi 平均吞吐 > 500 KB/s 或前台 APP 在白名单、3.2 BT 文件传输/音乐/电话、3.3 系统应用触发扫描；恢复扫描满足任一即可：4.1 WiFi 吞吐 < 100 KB/s、4.2 WiFi 断开路由器。

- **4.1 被违反（确定）**：两次 SCO 期间 WiFi 每秒吞吐都 ≤ 20 KB/s（SCO1 峰值 10.6 KB/s、SCO2 峰值 19.5 KB/s），一直低于 100 KB/s，扫描却一直挂起到 SCO 断开；原因是 SCO 期间 `ignoreWifiMsg=true`，WiFi 吞吐变化被忽略
- **3.1 缺乏依据（待确认）**：吞吐 > 500 KB/s 不成立（均值约 2 KB/s，不到门限的 1%；整份日志峰值也只有约 58 KB/s）；10:34:09 `wifi_high_tput: 1` 时吞吐也只有约 6.8 KB/s，当时前台为拨号器；日志中没有前台白名单判定记录，`wifi_state` 置 1 与 `STATE_AUDIO_CONNECTED` 同一毫秒发生。SCO 建立时前台为来电界面 `com.sh.smart.caller/InCallActivity`，需 BT 确认拨号器是否在白名单
- 结论："设计如此" 的答复不成立，实现与设计要求不符，应退回 BT 框架修正

## 问题窗口统计

| 阶段 | kernel 均值 / 峰值 (Mbps) | tcpdump 均值 (Mbps) | kernel lv |
|------|------|------|------|
| 通话前 10:33:30-10:34:04 | 0.012 / 0.117 | 0.014 | 0 |
| P2P 在线 10:34:04-10:34:08 | 0.070 / 0.093 | 0.090 | 0 |
| **SCO1 10:34:12-10:34:53** | **0.018 / 0.085** | **0.024** | 0 |
| 两次 SCO 之间 | 0.011 / 0.062 | 0.017 | 0 |
| **SCO2 10:35:27-10:35:50** | **0.017 / 0.156** | **0.022** | 0 |

- SCO 建立次数 2，每次都触发 BLE 扫描挂起（2/2）；iotservice startScan 被拒绝 1 次
- kernel `lv` 分布：`lv:0` × 201（100%）

## 排查步骤

1. main log 检索 `TranCoexMonitorComponentImpl` / `isCoexState` / `handleWifiTpOn` / `suspend ble scan`，确认共存态进入/退出时刻与 SCO（`ACTION_AUDIO_STATE_CHANGED newState:12/10`）是否对齐
2. 检查 SCO 前是否有 `wifi_high_tput` 上报，以及 `wifi_state` 是否在 SCO 同一毫秒由 0 变 1（`ignoreWifiMsg: true` / `persist=true`）
3. kernel `kalPerMonUpdate` 统计共存态期间的 `Tput` 与 `lv`（注意 kernel 时间为 UTC，需要加时区偏移）
4. tcpdump 按阶段统计字节数交叉验证
5. 排除 WiFi 侧异常：P2P/STA 断连、扫描失败、固件异常

## 关键日志

```
// 第一次 SCO：共存态挂起 + 拒绝 iotservice 扫描
10-12 10:34:12.128200 I TranCoexMonitorComponentImpl: BluetoothHeadset.STATE_AUDIO_CONNECTED and ignoreWifiMsg: true
10-12 10:34:12.128690 I BtScan.ScanManager: handleWifiTpOn persist=true, liveCoex=true, wifiTp=true
10-12 10:34:12.128704 I BtScan.ScanManager: isCoexState is true, suspend ble scan
10-12 10:34:24.755838 E BtScan.ScanManager: isCoexState active, not support start scan for system app ScanClient(packageName=com.transsion.iotservice, uid=1000, id=1, mode[LOW_POWER, used=LOW_POWER])

// 第二次 SCO：没有 WiFi 上报，SCO 一连上即 wifi_state=1
10-12 10:35:26.495227 I TranCoexMonitorComponentImpl: sendCoexBroadcast wifi_state: 0 bt_state: 0 ... hfp_playing: false ... wifi_ftp_On: false
10-12 10:35:26.946367 I TranCoexMonitorComponentImpl: BluetoothHeadset.STATE_AUDIO_CONNECTED and ignoreWifiMsg: true
10-12 10:35:26.946415 I TranCoexMonitorComponentImpl: sendCoexBroadcast wifi_state: 1 bt_state: 2 ... hfp_playing: true ... wifi_ftp_On: true
10-12 10:35:26.948645 I BtScan.ScanManager: isCoexState is true, suspend ble scan

// WiFi 实际吞吐（kernel +8h）
10-12 10:34:09.272 kalPerMonUpdate ... Tput 0.054mbps ... lv:0
10-12 10:35:29.168 kalPerMonUpdate ... Tput 0.156mbps ... lv:0
```

## TAG
- BT/WiFi共存
- isCoexState
- TranCoexMonitor
- BLE扫描被拒
- HFP/SCO
- 多端互联
- AIOT
- P2P连接成功
- 5G频段
- MTK平台
- Windows
- 非WiFi问题
- X6765

## 建议措施
1. **（BT 框架，首要）** SCO 建立时不要强制 `wifiTp=true` / `persist=true`，只采用 WiFi 实测高吞吐信号（如驱动 `kalPerMonUpdate lv` 档位，或框架 tput 监控连续 N 秒超阈值）；SCO 期间不要忽略 WiFi 的 "高吞吐解除" 消息
2. **（BT 框架 / 产品）** 对用户前台主动发起的设备发现（iotservice 多端互联、配对页），在共存态下改为低占空比放行或限时放行，而不是直接拒绝；至少向上层返回明确的错误码
3. **（WiFi / 框架）** 核查 `wifi_high_tput` 上报源的阈值与去抖逻辑（本案在约 0.05 Mbps 时上报为 1），并补充日志
4. **（互联应用）** 扫描被拒后提示用户，或在 `resume ble scan` 后自动重试

## 关联案例
- **CASE-031 / PWR-001**（弱相关）：BT 扫描 + Connsys BTWIFI 相关，但属于功耗问题，性质不同

## 分析报告
- `AI-result/issues/TOS170-36313/TOS170-36313-analysis.md`
- 本地日志：`AI-result/issues/TOS170-36313/logs/`
