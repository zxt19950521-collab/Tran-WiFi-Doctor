# CASE-017: 强 WiFi 下抖音 HEVC 硬解超时导致加载卡顿（滑走再回可播）

## 基本信息
- **案例ID**: CASE-017
- **分类**: performance
- **来源**: X6878OS16-11111
- **创建时间**: 2026-06-16
- **匹配次数**: 0

## 现象描述
- 中国粉丝刷 **抖音**（`com.ss.android.ugc.aweme`）时视频**进度条加载卡顿**；滑到下一个视频再滑回来可继续播放，过一会又卡
- 机型 Infinix X6878，Android 16 / XOS 16.2.0（X6878-16.2.0.145SP04 FANS），**Qualcomm** 平台（wcn6450）
- WiFi SSID **钱小乖.4G**（2.4G），RSSI **-30~-43 dBm**；偶现
- 问题时间 2026-06-15 **22:02:59**；录屏 `Screen_Recording_20260615_220208.mp4`（22:02:08~22:02:32）
- 工单评论：卡顿表现为**进度条加载**，已转三方；WiFi 组需确认网速是否异常

## 根因结论

**WiFi 链路全程正常，不构成根因；卡顿来自抖音播放链路的 HEVC 硬件解码输出缓冲周期性超时（~10s）叠加音频 underrun。**

机理链条：
1. **WiFi 排除**：全程无 `DISCONNECTED`/`network lost`；Ping **4~38ms 全 success**；Probe **196~371ms 全 success**；`WifiNetworkQuality: rssi sufficient` + `tput greater than NO_INTERNET_TRAFFIC`
2. **解码停滞**：`QC2V4l2Decoder [v4lhvcD_xx] Allocating output buffer timedout, ~10050ms`（≥6 次，21:17/21:36/21:43/21:44 等）→ 画面停、加载圈
3. **音频断供**：`AudioFlinger: BUFFER TIMEOUT underrun` / `AudioTrack: underrun, restarting`；录屏时段 22:02:13~28 密集
4. **用户「滑走再回能播」**：切换 feed 重建播放器/预加载，绕过卡死的 decoder 会话
5. **加重因素**：抖音主进程 **~1799MB**（22:01:39 memoryleak_detector）；22:01:36 LMK/kswapd 内存压力；22:02:08 录屏（MIC+内录）争用 Codec

与 CASE-012 区别：本单非 App 误报网络不可用，而是**加载进度条**；与 CASE-006/008 区别：本单**强信号、无 PER/吞吐塌陷**。

## 排查步骤

### 第一步：排除 WiFi（本案例可快速闭环）
1. main_log 搜 `WifiNetworkCheck` Ping/Probe → 是否全程 `success=true`
2. 搜 `DISCONNECTED`/`network lost`/`tear down wlan0` → 应为 **0**
3. `TranWifiSmartAssistantController: ====>>rssi` → 是否持续优良（如 >-50 dBm）
4. `WifiNetworkQuality` → 是否 `rssi sufficient` + `tput greater than NO_INTERNET_TRAFFIC`

### 第二步：确认播放/解码管线
1. 搜 `QC2V4l2Decoder` + `Allocating output buffer timedout` → 对齐用户卡顿时刻
2. 搜 `C2BqBuffer: last successful dequeue` → 解码队列空
3. 搜 `AudioFlinger: BUFFER TIMEOUT` / `AudioTrack: underrun` → 音频缓冲耗尽
4. 对照用户是否**滑走再回**可播 → 支持单条 feed decoder 卡死假说

### 第三步：加重因素
1. `memoryleak_detector` / `com.ss.android.ugc.aweme` 内存占用
2. `lmkd` / `kswapd` / PSI memory 是否同期升高
3. `RecordingService` 录屏是否与 underrun 集群重叠

### 第四步：三方跟进（主责）
1. 抖音 TTNet/播放器 verbose log：区分 CDN 下载慢 vs 下载正常解码失败
2. `dumpsys media.codec` 卡顿瞬间快照
3. 关录屏、清后台长时复现对比

## 关键日志

```
// WiFi 正常（申报前）
06-15 22:02:00.423772  TranWifiSmartAssistantController: ====>>rssi :-43
06-15 22:02:00.423987  WifiNetworkQuality: current rssi is sufficient
06-15 22:02:00.424437  WifiNetworkQuality: tput greater than NO_INTERNET_TRAFFIC
06-15 22:01:28.968734  WifiStatistics:WifiNetworkCheck: Ping result: {success=true, time=24ms}
06-15 22:00:59.295186  WifiStatistics:WifiNetworkCheck: Probe result: {success=true, time=371ms, response=204}

// HEVC 解码超时（典型）
06-15 21:36:58.384972  QC2V4l2Decoder: [v4lhvcD_54] Allocating output buffer timedout,
    10051ms elapsed since last input buffer queued (threshold 10000ms)
06-15 21:44:24.324949  QC2V4l2Decoder: [v4lhvcD_54] Allocating output buffer timedout, 10046ms ...

// 录屏时段音频 underrun
06-15 22:02:13.456259  AudioFlinger: prepareTracks_l BUFFER TIMEOUT: remove track(69) ... underrun
06-15 22:02:28.832654  AudioFlinger: prepareTracks_l BUFFER TIMEOUT: remove track(62) ... underrun

// 抖音高内存
06-15 22:01:39.156025  memoryleak_detector: report app memory leak success. name:com.ss.android.ugc.aweme
    pid:20278 ... 1799MB
```

## 建议措施

### WiFi 模块
- 本类单可闭环：**网速/时延/连接无异常**，退回三方/多媒体
- 附 Ping/Probe/RSSI 证据，无需改码

### 三方 / 多媒体（主责）
- 分析 QTI HEVC decoder 与抖音播放器会话兼容性
- 评估高内存 + 录屏资源争用
- 与字节跳动确认机型/版本已知问题

## 相关案例
- **CASE-012**（TOS163-35222）：系统 WiFi 正常但 App 层网络异常（误报），鉴别思路类似
- **CASE-006/008**：弱信号/PER 高导致卡顿 — 本单**不匹配**（强信号、无空口拥塞）

## 分析报告
- `AI-result/issues/X6878OS16-11111/X6878OS16-11111-analysis.md`
