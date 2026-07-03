# CASE-022: WhatsApp 视频通话 PiP 副画面模糊（WiFi 链路正常）

## 基本信息
- **案例ID**: CASE-022
- **分类**: performance
- **来源**: KN6OS16-2806
- **创建时间**: 2026-06-26
- **匹配次数**: 0

## 现象描述
- 肯尼亚粉丝反馈：WiFi 环境下 WhatsApp 视频通话，**全屏主画面清晰，PiP 副画面（secondary feed）明显模糊/马赛克**，影响通话体验。
- 机型 TECNO CN6c (XYZ)，Android 16 / HiOS 16.3.0，MTK 平台。
- 应用：WhatsApp `com.whatsapp`，界面 `VoipActivityV2`。
- WiFi SSID **Kul Joe**（2.4GHz ch1，BSSID e8:ab:**:**:**:70）。
- 用户截图 `Screenshot_20260623-210759.jpg` / `210803.jpg` 时间约 **21:07:59 / 21:08:03**；Jira 锚点 **21:09:24**（Africa/Nairobi）。
- 关键：WiFi 全程连接、RSSI 强、吞吐量正常、状态栏 WiFi 满格且实时速率 **872 KB/s / 597 KB/s**；不是断连、弱信号、漫游或 WifiNetworkQuality 断连类 WiFi 故障。

## 根因结论
**WhatsApp 视频通话在 PiP/副画面窗口使用低 tier 视频流或低分辨率渲染路径，而对端/全屏主画面保持较高质量；WiFi 链路 RSSI/tput/PHY 速率均正常，副画面模糊属于应用层 adaptive video / 解码分配问题，非 WiFi 驱动/RF/漫游故障。**

机理链条：
1. 21:06:39 `VoipActivityV2` 启动，21:07:36 起同时存在两路渲染：**Activity#1895**（全屏 UI/主画面）与 **SurfaceView BLAST**（远端视频 tile / 副画面）。
2. 粉丝截图：一帧全屏远端模糊、PiP 本地清晰；另一帧全屏本地清晰、**PiP 远端副画面明显模糊**——主副画面质量不对称，且 WiFi 图标满格。
3. Framework `WifiNetworkQuality`（21:07–21:09，58 采样）：吞吐量均值 **~738**，全程 `current rssi is sufficient`、`tput greater than NO_INTERNET_TRAFFIC`；21:09:24 锚点 `17.71/760.67`。**无** `isHighPingDelay`、**无** wlan0 tear down / 漫游 / 断连。
4. Kernel `wlanLinkQualityMonitor`（localtime +3h 对齐本地 ~21:08–21:12）：Tx/Rx PHY **650–720 Mbps**，MovAvg RSSI **-35～-40 dBm**，链路稳定。
5. SurfaceFlinger：主层 VoipActivity fps 均值 **~17.1**（0.27–32.9），副 SurfaceView fps 均值 **~12.7**（4.9–20.0）——副画面持续刷新但帧率低于主层，模糊更符合**低分辨率解码/高压缩**，而非 WiFi 丢包导致的冻结。
6. 21:09:22 WhatsApp `msys` MNS TCP **Received EOF**（443 信令通道），随后 21:09:24 WiFi 质量仍正常，说明非 wlan 层断网。
7. 21:08 窗口大量 `AudioALSACaptureDataProviderNormal: TIMEOUT`（音频采集延迟 ~40ms），反映通话 CPU/音频调度压力，一般不单独导致“仅副画面模糊”。

## 排查步骤
1. 确认业务场景：
   - 搜 `VoipActivityV2`、`com.whatsapp.calling.ui`，对齐 Jira 锚点与截图时间。
   - 区分副画面是**远端小窗**还是**本地摄像头 PiP**（本案两帧截图主副角色互换，均有一路模糊）。
2. 排除 WiFi 断连/弱信号：
   - 查 `WifiNetworkQuality`、`TranWifiSmartAssistantController: mCurrentNetwork`、`CTRL-EVENT-DISCONNECTED`、`isHighPingDelay`、`torn down Iface.*wlan0`。
   - 本例全程连接 Kul Joe，无断连/高 Ping 时延 TAG。
3. 驱动链路质量：
   - kernel `.localtime` 需 **+3h** 对齐 Africa/Nairobi main_log。
   - 查 `mtk_cfg80211_get_station` RSSI/link speed 与 `wlanLinkQualityMonitor` Tx/Rx/PER。
   - 本例 RSSI -35~-40 dBm、PHY 650~720 Mbps，属强信号正常链路。
4. 应用渲染层：
   - 搜 `BufferQueueProducer` + `VoipActivityV2` / `SurfaceView[...VoipActivityV2](BLAST)` 的 `queueBuffer: fps=`。
   - 对比全屏 Activity 层 vs 副 SurfaceView 帧率；副画面 ~14 fps 且持续刷新 → 低 tier 码流/解码，非 0 帧卡死。
5. 排除 WiFi 后查 App/对端：
   - 搜 WhatsApp `msys`/`WebRTC`/`bitrate`/`jitter`（本案 WhatsApp 信令 EOF 不等于 WiFi 断连）。
   - 补 tcpdump 过滤 UDP/RTP、对端网络状况，区分“对端发送低码流” vs “本机 PiP 降采样”。

## 关键日志
```
// Voip 通话建立（main_log）
06-23 21:06:39  ... com.whatsapp.calling.ui.VoipActivityV2 ...
06-23 21:07:36  BufferQueueProducer: [VoipActivityV2#1895] queueBuffer: fps=12.20 ...
06-23 21:07:37  BufferQueueProducer: [SurfaceView[...VoipActivityV2](BLAST)#1903] queueBuffer: fps=14.53 ...

// 双路渲染 fps 对比（main_log，21:08 窗口）
06-23 21:08:00.536  [VoipActivityV2#1895] queueBuffer: fps=15.02 ...
06-23 21:08:01.871  [SurfaceView[...VoipActivityV2](BLAST)#1937] queueBuffer: fps=13.85 ...
06-23 21:08:08.996  [VoipActivityV2#1895] queueBuffer: fps=10.02 ...
06-23 21:08:09.295  [SurfaceView[...VoipActivityV2](BLAST)#1937] queueBuffer: fps=14.31 ...

// WiFi 质量正常（main_log，21:09:24 锚点）
06-23 21:09:24.963  WifiNetworkQuality: 17.71/760.67
06-23 21:09:24.964  WifiNetworkQuality: current rssi is sufficient
06-23 21:09:24.964  WifiNetworkQuality: tput greater than NO_INTERNET_TRAFFIC
06-23 21:08:00.850  TranWifiSmartAssistantController: mCurrentNetwork :100 SSID :"Kul Joe"

// Kernel 强信号高 PHY（kernel .localtime，+3h 对齐本地 ~21:09）
06-23 18:09:19  wlanLinkQualityMonitor: Tx(rate:720,...), Rx(rate:722,...), ...
06-23 18:09:19  mtk_cfg80211_get_station: link speed=720/722, MovAvg_rssi=-40, ...

// WhatsApp 信令 EOF（非 WiFi 断连）（main_log）
06-23 21:09:22.825  msys: WAJMNSStream/impl/callback/onMNSFailure ... Received EOF
06-23 21:09:22.826  msys: ... state-changed ... (connected=>disconnected)
```

## TAG
- WiFi未断开
- WiFi链路正常
- 非WiFi问题
- 第三方App视频通话
- WhatsApp
- VoipActivityV2
- PiP副画面模糊
- secondary feed degraded
- 主清晰副模糊
- 应用层自适应码流
- SurfaceView BLAST
- WifiNetworkQuality正常
- RSSI强信号
- PHY速率高
- 2.4G ch1
- 粉丝反馈
- 肯尼亚
- CN6c
- MTK平台

## 建议措施
1. 定性为 **WhatsApp 视频通话体验 / 第三方 App** 问题，WiFi 组可出具“链路正常”结论后转 App 或粉丝复测。
2. 同 AP 对比 **REF 竞品机** WhatsApp 1v1 视频通话 PiP 是否同样模糊，确认是否为 App 通用行为。
3. 分别测试 WiFi / 4G 是否仅 WiFi 复现；本案 WiFi 质量优于典型弱网，若仅 WiFi 复现需补 **tcpdump（UDP/RTP）** 再查 QoS。
4. 记录副画面角色（远端 vs 本地摄像头），对端网络差也会导致远端 PiP 模糊。
5. 不建议按 MTK WiFi 驱动 bug、漫游、扫描失败提 CR——缺乏链路层证据。

## 数据局限
- 无 tcpdump 和有效空口日志（picus 仅 30B），无法定量 RTP 丢包/jitter。
- 无 WhatsApp 内部 call stats，无法区分对端低码流 vs 本机 PiP 解码降采样。
- 21:09:24 锚点 VoipActivity 日志已减少（末条 ~21:08:35），主分析窗口以 21:07–21:08 截图时刻为准。

## 相关案例
- **CASE-012（TOS163-35222）**：同属“应用层体验 vs WiFi 链路状态不一致”。区别：CASE-012 为 Shopee 断网误报 + WifiNetworkQuality tear down；本例 WiFi 全程正常，副画面模糊。
- **CASE-020（TOS163-38141）**：同为 App 层体验问题。区别：CASE-020 有弱信号、10/10Mbps、`isHighPingDelay`、Ping 1s timeout；本例 RSSI 强、PHY 高、tput 正常。
- **CASE-021（X6887OS16-3257）**：同为 WiFi 链路正常但 App 体验异常。区别：CASE-021 为 Rapid VPN 导致 IPv4 路径失败；本例无 VPN，为视频 PiP 渲染/码流 tier 问题。
- **CASE-017（X6878OS16-11111）**：同涉及视频解码/卡顿。区别：CASE-017 为抖音 HEVC 解码超时；本例 WiFi 正常、WhatsApp Voip PiP 低分辨率。
