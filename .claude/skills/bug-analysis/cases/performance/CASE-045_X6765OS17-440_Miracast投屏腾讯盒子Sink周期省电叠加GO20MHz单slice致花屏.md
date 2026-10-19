# CASE-045: Miracast 投屏腾讯极光盒子6 播放视频花屏——Sink 周期性省电突发 + GO 20MHz 1x1 + 单 slice/IDR 4s

## 基本信息
- **案例ID**: CASE-045
- **分类**: performance
- **来源**: X6765OS17-440
- **创建时间**: 2026-10-16
- **匹配次数**: 0

## 现象描述
- X6765（X6765-17.0.0.039SP01，PR0）镜像投屏到**腾讯极光盒子6**（LIVE555 WFDSink），播放本地视频时**必现花屏**：全屏偏绿、马赛克拖影、白色块状条纹，每次持续几秒后自动恢复
- P2P、RTSP 全程**不断开**；手机为 P2P GO，5180 MHz ch36；STA 未连接（无 MCC）
- 日志路径 `\\10.205.4.20\sw_log\通信测试Log\X6765\qing.fang1\X6765OS17-440`（含空口抓包和现象录像）

## 根因结论
**盒子（GC）每 10.0 s 进入约 1.6 s 的 PM 省电/离信道突发（约 14 次 76~84 ms 睡眠，突发内约 69% 不在线）。手机 GO 只以 20 MHz 1x1 工作（CNM 已授权 40 MHz，`rlmBssInitForAP` 却设为 SCO=0），同信道还有邻居 AP 竞争。突发期间 MAC 时延 >50 ms，部分帧重传用尽被丢弃（Txfail），导致 RTP 丢包。码流为 1080p60、17.6 Mbps、每帧 1 slice、IDR 4 s，且 Sink 从不请求 IDR，少量丢包即造成整帧花屏并持续到下一个 IDR。**

机理链条：
1. Sink 周期性 Null(PM=1) 突发 → GO 暂停发送（不发 RTS），队列积压
2. 唤醒窗口只有约 22 ms，加上 20 MHz 1x1（VHT MCS7/8）和同信道竞争 → 积压消化不及
3. MAC 时延 >50 ms → 重传用尽 → Txfail（MSDU 丢弃）→ RTP 包丢失或迟到
4. 单 slice 帧损坏，P 帧误差扩散 → 花屏，直到下一个 IDR（最多 4 s）

量化证据：
- 35/35 个 Txfail 窗口落在突发内；MAC 时延 >50 ms 的 100 秒中有 98 秒在突发内
- MAC 时延 ≥20 ms 的 MSDU 占比：突发内 33.3%，突发外 1.8%
- RTCP RR 累计丢包 11 个（约 62 万包），6 次增量全部落在含突发的窗口内
- 录像花屏时刻（16:37:01~04、16:37:49~52）与丢包窗口和 IDR 时间吻合
- 信号良好：RCPI 中位数约 −52.75 dBm，花屏时约 −45 dBm，link_score 为 100

## 排查步骤
1. **先排除断连、编码器和 MCC**：
   - P2P/RTSP 是否全程在线，keep-alive 是否正常
   - `C2MtkVenc: IDR frame produced` 是否按周期输出；Source 端 RTP 序号是否连续
   - 会话期间是否有 STA 连接、扫描、RoC、NoA（本案均无）
2. **WFD 编码参数**（main log，`MtkConverter`）：`i-frame-interval`、`wfd.slice-count`、`video_bitrate`、分辨率和帧率；检查 Sink 是否发送 `wfd_idr_request`
3. **GO 带宽 / 空间流**：
   - kernel：依次对比 `mtk_p2p_cfg80211_start_ap channel[...]`（上层请求）、`ChReq ... w(vht)= s1=`（驱动申请）、`ChGrant ... sco=`（授权）、`rlmBssInitForAP: SCO= BW= TxN= RxN=`（BSS 实际配置），以及 `cnmOpModeGetTRxNss BSS[x](MAX_CAP)`。
   - FW：查 `CAL: SwCh Param ... Bw() F()`、`IDC BssInfo` 的频率上下限，以及 `RA_x: raUpdateTxRateCode` 中的 BW/NSS。
   - 空口：Beacon 中 HT/VHT Cap 与 Operation 字段的宽度。
4. **发送时延和丢弃**（kernel）：`halDumpMsduReportStats` 的 M 桶（>50 ms 占比）和 `Txfail`；`nicUpdateStaStats (P2P)` 的 RCPI、fail_cnt 用于排除信号弱
5. **空口**：统计 GC 的 Null PM=1/0 序列，识别周期性突发（周期、持续时长、不在线占比）；统计同信道其他 BSS 的负载
6. **tcpdump**：解析 Sink 回传的 RTCP RR（cumLost、jitter），定位丢包窗口
7. **四路对时**：用 GO Deauth 等锚点对齐空口、kernel（UTC+8）、tcpdump 和录像，逐一核对花屏时刻

## 关键日志
```
// GO 已获 40 MHz 授权，但实际为 20 MHz 1x1（kernel UTC）
cnmChMngrHandleChEvent:(CNM INFO) ChGrant net=1 band=0 token=7 ch=36 bw=0 sco=1 s1=38 s2=0
rlmBssInitForAP:(RLM INFO) WLAN AP SCO=0 BW=0 S1=36 S2=0 CH=36 Band=2 TxN=1 RxN=1

// WFD 编码参数（main log）
MtkPlaybackSession: selectOprate: video 1920x1080@60, codecType=1, profile=8
MtkConverter: user set video_bitrate=17600000
MtkConverter:   int32_t i-frame-interval = 4
MtkConverter:   int32_t wfd.slice-count = 1

// 花屏时刻（16:37:49）：信号好但 96% 的 MSDU MAC 时延 >50 ms，并出现 Txfail
halDumpMsduReportStats: TX_Delay ... M:[5:10:20:50]=[879:329:164:91:147#13] ... Txfail:3
nicUpdateStaStats:(P2P INFO) [1][9] link_score=100, rssi=125, rate=156, threshold_cnt=0, fail_cnt=40
halDumpMsduReportStats: TX_Delay ... M:[5:10:20:50]=[0:0:36:19:1389#141] ... Txfail:1

// 空口：GC 周期性 PM 突发
GC Null PM=1 → 约 76–84 ms → PM=0 → 醒来约 22 ms → PM=1 …（每突发约 14 次，约 1.6 s，周期 10.00 s，共 90 次）

// RTCP RR（tcpdump）
cumLost 1→12；增量窗口 16:30:53(+1) 16:31:46(+1) 16:33:42(+1) 16:36:58(+4) 16:37:48(+3) 16:38:04(+1)
```

## TAG
- Miracast
- WFD
- 投屏
- 花屏
- 腾讯极光盒子
- P2P-GO
- 5G频段
- MTK平台
- MtkWifiDisplaySource
- Sink周期性省电
- GC离信道
- MAC时延高
- Txfail
- RTP丢包
- RTCP
- GO 20MHz 1x1
- 带宽回落
- 同信道竞争
- 单slice
- IDR间隔4s
- 无IDR请求
- 非断连
- 非MCC
- 信号良好
- X6765

## 建议措施
1. **WiFi 驱动**：固件日志确认固件只是执行者，降带宽发生在驱动，分两步：上层 `start_ap` 请求 80 MHz（`channel[1 3 5180 5210]`）→ 驱动 `ChReq w(vht)=0 s1=38` 只申请 40 MHz → `rlmBssInitForAP SCO=0` 降到 20 MHz。40 MHz 授权只在建 GO 的 3 s 内生效，`ChAbort` 后固件 `SwCh Bw(0) F5180` 回到 20 MHz。已排除 BT/LTE 共存和 DBDC。GO 的 1x1 是 BSS1 的 `MAX_CAP T:1 R:1`（STA 为 2x2）。需确认 P2P GO 的带宽/SCO/NSS 策略或 wifi.cfg 配置，在单 GO（无 MCC）场景下放开 40/80 MHz。盒子 STA_REC 的 VHT MCS Map 为 0xfffe（疑似 1SS），所以带宽才是主要收益
2. **投屏/多媒体**：`i-frame-interval` 由 4 s 改为约 1 s 或启用 intra-refresh；`wfd.slice-count` 由 1 改为 4~8；根据 RTCP cumLost 增量主动插入 IDR；评估对此类 Sink 使用 1080p30 或更低码率
3. **GO 自适应（可选）**：检测到 Sink 周期性 PM 突发时，适当延长重传/生存时间或降低码率
4. **Sink 侧**：请腾讯确认 WFD 会话期间每 10 s 一次的后台扫描/省电行为，建议投屏期间关闭或缩短
5. **复测**：换到空闲信道复测；补充对比机的 tcpdump、空口和录像

## 数据局限
- 盒子离信道的原因（扫描 / BT 共存 / 省电）只能从空口推断，没有盒子侧日志
- tcpdump 仅覆盖 16:29:54 之后；没有对比机数据
- FW `.clog` 只解码了明文记录（`55 00 00 62` 头 + 字符串，用 `timesync` 记录对时，tick 为 32.768 kHz）；`0xA8` 二进制索引记录和 WIFIMCU 文件需 MTK 字典；connsys picus log 为空
- 空口抓包从关联之后才开始，未能直接核实盒子的 HT/VHT 能力

## 相关案例
- **CASE-016（X1102COS16-184）**：同为 Miracast / MtkWifiDisplaySource，但根因是 VCodec 初始化失败导致 Source 主动 TEARDOWN（连接失败类）
- **CASE-009（CN6OS16-1398）**：同为 Miracast，但根因是 P2P 形成失败或 Sink 未发起 RTSP（连接失败类）
- **CASE-032**：链路瞬时恶化导致视频卡顿，属同一类“链路瞬时恶化 → 视频体验问题”
- **鉴别要点**：连接正常但画面花屏/马赛克时，先看 Sink 的 RTCP cumLost 和 GO 的 Txfail / MAC 时延，再看 Sink 是否有周期性 PM 突发，以及 GO 带宽和编码 slice/IDR 参数
