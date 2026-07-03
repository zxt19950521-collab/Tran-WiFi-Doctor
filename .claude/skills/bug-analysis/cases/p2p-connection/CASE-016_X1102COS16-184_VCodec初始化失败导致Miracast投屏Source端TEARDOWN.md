# CASE-016: X1102C Miracast 投屏 VCodec 编码器初始化失败导致 Source 端 RTSP TEARDOWN（WiFi/P2P 通路正常）

## 基本信息
- **案例ID**: CASE-016
- **分类**: p2p-connection
- **来源**: X1102COS16-184（原 TOS163-963）
- **创建时间**: 2026-06-17
- **匹配次数**: 0

## 现象描述
- X1102C PAD（STR3）下拉控制中心 → 投放 → 连接**小米盒子** Miracast 投屏
- **必现（must）**：界面显示连接成功后又突然断开，无法再次连接
- 风险 5/5；日志路径 `\\10.207.190.10\sw_log\系统测试Log\qiankai.zhang\TOS163-963`
- 工单最终归属 **(Drv)Video Codec** 模块（非 WiFi）

## 根因结论
**WiFi P2P GO/GC 与 RTSP 信令通路正常；投屏断开是因为 MTK VCodec 硬件编码器 `c2.mtk.avc.encoder` 初始化失败（setOutputFormat fail / Output format nullptr），`MtkWifiDisplaySource` 无法产出视频帧后主动发送 RTSP TEARDOWN 退出会话。**

机理链条：
1. P2P 组建立、GO/GC 关联、RTSP 协商启动（WiFi 层无异常）
2. Source 启动 AVC 编码器 → V4L2Device 输出格式为 nullptr → `setOutputFormat fail`
3. `C2MtkVenc FatalError(InitError)` → MediaCodec `UNKNOWN_ERROR`
4. 无视频帧 → `MtkMediaSender: audio is waiting for video data to come drop audio`（音频被反复丢弃）
5. `playback session wants to quit` → `Sending TEARDOWN` → 用户感知投屏断开

## 排查步骤
1. **先区分失败层**（避免误判为 WiFi 问题）：
   - 搜 `P2P-GROUP-FORMATION-FAILURE` / `Mgmt Frame TX Fail` → P2P 层失败（见 CASE-009 模式 A）
   - P2P 成功时搜 `MtkNetworkSession: incoming connection` → 对端是否发起 RTSP（CASE-009 模式 B：无 incoming）
   - **本案特征**：有 RTSP 交互，但 Source 主动 `Sending TEARDOWN` / `playback session wants to quit`
2. **编码器链路**（主因定位）：
   - 搜 `C2MtkVenc` / `c2.mtk.avc.encoder` / `setOutputFormat fail` / `FatalError(InitError)`
   - 搜 `MtkMediaSender: audio is waiting for video data` → 佐证编码器未出帧
3. **WiFi 层快速排除**：
   - 确认 `P2P-GROUP-STARTED`、`EAPOL-4WAY-HS-COMPLETED`、DHCP 正常
   - 若 RTSP TEARDOWN 紧跟 VCodec 错误，则 WiFi 非主因
4. **工单归属**：确认是否应转 Video Codec / 平台 bring-up（X1102 modem 适配备注）

## 关键日志
```
// WiFi 层结论（分析备注）
wifi GO/GC正常连接，RTSP协商过程中source端主动teardown，通路正常，投屏业务协商中断

// VCodec 初始化失败（12-25 03:50:33）
VCodec : [V4L2Device] Set Format Output format is *nullptr*
VCodec : [OutputFormat] *setOutputFormat fail*
C2MtkVenc: FatalError(InitError) event, call back error to client
CCodec : Component "c2.mtk.avc.encoder" returned error: 0xe
MediaCodec: Codec reported err 0x80000000/UNKNOWN_ERROR, while in state 6/STARTED

// 编码器无视频 → 音频丢弃
MtkMediaSender: ***audio is waiting for video data to come drop audio *****

// Source 主动断开 RTSP
MtkWifiDisplaySource: playback session wants to quit.
MtkWifiDisplaySource: Sending *TEARDOWN* trigger.
MtkWifiDisplaySource: received a request method = TEARDOWN
MtkWifiDisplaySource: Destroying PlaybackSession
```

## TAG
- Miracast
- WFD
- 投屏
- 小米盒子
- X1102C
- PAD适配
- P2P正常
- RTSP TEARDOWN
- Source主动断开
- MtkWifiDisplaySource
- MtkMediaSender
- VCodec
- C2MtkVenc
- c2.mtk.avc.encoder
- setOutputFormat fail
- InitError
- MediaCodec UNKNOWN_ERROR
- 编码器未出帧
- drop audio
- 非WiFi问题
- Video Codec
- MTK平台

## 建议措施
1. **Codec 主责**：修复 X1102C 平台 `c2.mtk.avc.encoder` V4L2 输出格式配置；核对 WFD 协商分辨率/帧率与 encoder capability
2. **平台 bring-up**：关注 X1102 modem/视频子系统适配进度（工单备注：待 T1103 modem 调整后验收）
3. **WiFi 分流**：同类 Miracast 失败先查三层——P2P 形成 / RTSP 连接 / 编码器启动；本案属第三层
4. **复测**：修复后确认无 `FatalError(InitError)`、无持续 drop audio、投屏可持续

## 数据局限
- 本地未下载完整 TagLog（UNC 路径不可达）；结论来自 Jira 评论摘录的 main_log 片段
- 无 kernel log，未验证链路质量/RSSI/PER；WiFi "通路正常" 依赖团队分析结论
- 无空口/tcpdump

## 相关案例
- **CASE-009（CN6OS16-1398）**：同为 Miracast/WFD/MtkWifiDisplaySource。区别：
  - CASE-009 **模式 A**：P2P 组形成失败（Mgmt Frame TX Fail）
  - CASE-009 **模式 B**：P2P+DHCP 成功，**Sink 未发起 RTSP**（无 incoming connection）
  - **CASE-016**：P2P+RTSP 通路正常，**Source 因 VCodec 失败主动 TEARDOWN**
- **CASE-003（OS162-40436）**：同为"链路成功、上层失败"，但失败在 DHCP 而非编码器
- **鉴别要点**：看 TEARDOWN 发起方（Source vs Sink）、TEARDOWN 前是否有 VCodec/MediaCodec 错误、是否有 incoming RTSP 连接
