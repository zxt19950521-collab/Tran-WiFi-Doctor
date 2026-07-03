# CASE-020: Facebook 弱信号高时延导致图片/视频灰屏加载慢（WiFi 未断开）

## 基本信息
- **案例ID**: CASE-020
- **分类**: performance
- **来源**: TOS163-38141
- **创建时间**: 2026-06-25
- **匹配次数**: 0

## 现象描述
- 肯尼亚粉丝反馈：即使在“强 Wi-Fi”下，Facebook 视频和图片加载不顺，出现灰屏占位。
- 机型 TECNO CN6c，Android 16 / HiOS 16.3.0，MTK 平台。
- 应用：Facebook `com.facebook.katana`，版本 `565.0.0.49.74`。
- 用户截图 `Screenshot_20260617-091015.jpg` 顶部时间约 `09:10`，系统截图日志对齐 `2026-06-17 09:10:15`。
- 关键：WiFi 全程保持连接并持续 `Wifi network validated`，不是断连、DHCP 失败、DNS 失败或应用单独异常；问题窗口是弱链路/高时延导致的内容加载慢。

## 根因结论
**RSSI 弱、物理速率坍塌到 10/10 Mbps、PER 突刺和 ACK fail 主导的上行链路质量差，导致系统 Ping/Probe 多次 1s 超时，Facebook Feed 图片/视频灰屏或加载慢；当前信道 ch5 AP 不密集，但存在短时空口活动突发，会叠加弱信号放大高时延。**

机理链条：
1. 截图时刻 Facebook 在前台，WiFi 仍连接 `Staffroom` 且框架层持续 `Wifi network validated`，排除 WiFi 断开、DHCP/IP 配置丢失和 Connectivity 完全失效。
2. 问题窗口内 `WifiNetworkQuality` 连续上报 `isHighPingDelay : true , hasInternetAccess : true`，系统 Ping/Probe 多次 `1000ms` 超时，说明网络可用但 RTT/探测时延异常。
3. kernel 对齐本地 `09:08~09:10` 显示 `MovAvg_rssi=-76~-74 dBm`，link speed 和 `wlanLinkQualityMonitor` 均降到 `10/10 Mbps`。
4. 截图秒点 `PER(91)`，累计 Tx fail 中 ACK fail 占比约 `95.7%`，说明 STA 发出的数据帧收不到 AP ACK，是上行可靠性差/弱链路的典型表现。
5. 全信道扫描显示当前连接在 2.4G ch5，AP 数不多，`BAndPCnt` 多数 `0~3`，不属于 AP 密集型拥塞；但 ch5 `IdleTime` 多次低值、`MdrdyCnt` 可达 `232`，存在短时空口活动突发。
6. 对比 `08:55-08:57`：RSSI `-52~-38 dBm`、Tx/Rx rate 高、网络仍 validated，Ping 大多成功，但已有零星 Probe/Ping timeout，说明当时网络可用但已有轻微抖动；真正导致用户截图灰屏的是 `09:10` 附近弱信号和速率坍塌后的高时延。

## 排查步骤
1. 框架层确认是否真断网：
   - 搜 `Wifi network validated`、`mCurrentNetwork`、`CTRL-EVENT-DISCONNECTED`、`Wifi network lost`、`CMD_IP_CONFIGURATION_LOST`。
   - 本例问题窗口无断开/tear down/IP lost，WiFi 仍为 validated。
2. 业务时间锚点对齐：
   - Jira 最后发生时间为 `09:08:30`。
   - 用户截图文件名和系统 `GlobalScreenshot` 对齐 `09:10:15`，应优先以截图时刻作为主锚点。
3. 网络探测：
   - 查 `WifiStatistics:WifiNetworkCheck` 的 `Ping result` / `Probe result`。
   - 本例 `09:08:15/25/35/45`、`09:09:55/56`、`09:10:15` 多次 1s timeout，但间歇仍 validated。
4. 驱动链路质量：
   - 用 kernel `.localtime`，本例 kernel 时间需 `+3h` 对齐 main_log。
   - 查 `mtk_cfg80211_get_station` 的 RSSI/link speed 和 `wlanLinkQualityMonitor` 的 Tx/Rx/PER/ACK fail。
5. 信道干净程度：
   - 从 `scnFsmDumpScanDoneInfo` 提取当前连接信道 ch5 的 AP 数、`IdleTime`、`MdrdyCnt`、`BAndPCnt`、`CU Value`。
   - 区分“AP 不密集”与“短时空口活动突发”。

## 关键日志
```
// 框架层：WiFi 已连接且持续 validated（main_log）
09:08:04 WifiStatistics:WifiNetworkCheck: Wifi network validated
09:08:05 TranWifiSmartAssistantController: mCurrentNetwork :1164 SSID :"Staffroom"
09:08:30 WifiStatistics:WifiNetworkCheck: Wifi network validated
09:10:07 WifiStatistics:WifiNetworkCheck: Wifi network validated
09:10:20 WifiStatistics:WifiNetworkCheck: Wifi network validated

// 高时延：问题窗口内 Ping/Probe 多次 1s 超时（main_log）
09:08:11 WifiNetworkQuality: isHighPingDelay : true , hasInternetAccess : true
09:08:15 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=1000ms}
09:08:25 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=1000ms}
09:08:35 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=1000ms}
09:09:55 WifiStatistics:WifiNetworkCheck: Probe result: {success=false, time=1000ms}
09:10:15 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=1000ms}

// 客户截图时刻：Facebook 前台灰屏与 Ping timeout 对齐（main_log）
09:10:11 fb4a.RageShakeDetector: onResume: com.facebook.katana.activity.FbMainTabActivity
09:10:15 GlobalScreenshot: cropTopAndBottomBitmap: com.facebook.katana
09:10:15 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=1000ms}

// driver：弱信号、速率坍塌、ACK fail 主导（kernel .localtime，+3h 对齐本地）
06:08:04 mtk_cfg80211_get_station: link speed=10/10, MovAvg_rssi=-76
06:08:05 wlanLinkQualityMonitor:
  Tx(rate:10, total:2704303, retry:9081, fail:83948, RTS fail:4243, ACK fail:79705),
  Rx(rate:55, total:67917, error:89), PER(0)

06:10:14 mtk_cfg80211_get_station: link speed=10/10, MovAvg_rssi=-74
06:10:15 wlanLinkQualityMonitor:
  Tx(rate:10, total:2712001, retry:10499, fail:105276, RTS fail:4515, ACK fail:100761),
  Rx(rate:10, total:70573, error:94), PER(91)

// 当前信道 ch5：AP 不密集，但有短时空口活动突发（scnFsmDumpScanDoneInfo）
06:08:29 SCANLOG: ucCompleteChanCount[37], used[3]
Channel: 1 2 3 4 5 6 7 8 9 10 11 12 13 36 ... 165
SCANLOG Total:3/3 Staffroom; KIANJOKOMA PRIMARY ; pb@kairuri M5
ch5: IdleTime=2205, MdrdyCnt=232, BAndPCnt=2, CU Value=0
```

## TAG
- WiFi未断开
- 第三方App加载慢
- Facebook灰屏
- RSSI低
- 协商速率低
- 延迟高
- Probe超时
- Ping超时
- ACK fail主导
- PER突刺
- 上行链路质量差
- 2.4G ch5
- AP不密集
- 信道空口活动突发
- MTK driver
- 粉丝反馈

## 建议措施
1. 用户/测试侧优先复测弱信号路径：靠近 AP、切 5G、更换信道或更优 AP 后复测 Facebook 加载耗时、RSSI、link speed 和 Ping 延迟。
2. 同位置对比机验证：记录本机与竞品的 RSSI、Tx/Rx rate、Ping/Probe、Facebook 首屏图片加载耗时，确认是否存在本机弱信号性能差异。
3. 补充 tcpdump 或空口日志：确认 Facebook HTTPS 请求是否被网络 RTT/重传拖慢，以及 802.11 层是否存在 AP 无 ACK、重传或外部干扰。
4. WiFi/RF 侧若内部可复现：重点看弱信号下 Tx rate 降速、ACK fail、天线/功率校准和 rate control 策略。
5. 回复口径：WiFi 未断开且系统仍 validated，但问题时刻链路质量差、Ping/Probe 超时，Facebook 灰屏与弱网高时延一致；不建议按 Facebook 单独应用问题关闭。

## 数据局限
- 无 tcpdump 和有效空口日志，无法逐帧证明 Facebook HTTPS 请求或 802.11 ACK/重传细节。
- `connsys_picus_log_*` 仅约 30 bytes，无法用于 WiFi FW/空口侧进一步分析。
- AP 上游网络、AP 负载、遮挡距离、非 WiFi 干扰之间的拆分，需要空口抓包和对比机数据进一步确认。

## 相关案例
- **CASE-006（LK7OS163-2073）**：同为弱信号、PER 高、速率坍塌、WiFi 未断开导致业务卡顿。区别：CASE-006 叠加单 AP 漫游失败和全频扫描；本例未见明显漫游失败，主线是 Facebook 加载慢和高 Ping。
- **CASE-015（OS162-41328）**：同为 ACK fail 主导、WiFi 未断开、数据面异常。区别：CASE-015 是中等 RSSI 下上行 TX path 异常叠加 ch11 争用，表现为已连接但无法上网/DNS 失败；本例是弱信号低速率下的间歇高时延，未完全断网。
- **CASE-008（LK7OS163-2102）**：同为 App 加载慢和 WiFi 未断开。区别：CASE-008 是强信号、速率正常下空口拥塞/同频干扰；本例截图时刻 RSSI 弱、速率坍塌到 10/10 Mbps，不能按强信号拥塞处理。
- **CASE-019（TOS163-37795）**：同有 Probe 失败。区别：CASE-019 的 Probe 失败触发 SmartAssistant SSID 乒乓和 network lost；本例无 network lost，仍停留在同一 SSID 的弱链路高时延状态。
