# CASE-009: CN6 Miracast投屏P2P成功但RTSP连接失败

## 基本信息
- **案例ID**: CASE-009
- **分类**: p2p-connection
- **来源**: CN6OS16-1398（原 TOS163-32888）
- **创建时间**: 2026-06-08
- **匹配次数**: 0

## 现象描述
- CN6（TECNO CAMON Slim 5G）向客厅盒子3498-Miracast投屏失败
- 问题版本 CN6-16.3.0.116：5/5 FAIL；复测版本 121：3 次中 2 成功 1 失败
- 存在两种失败模式：
  1. **P2P 层**：`P2P-GROUP-FORMATION-FAILURE`，手机作为 GO 时管理帧发送失败
  2. **RTSP 层**：P2P 四次握手 + DHCP 均成功，但对端未发起 TCP/RTSP 连接到 7236 端口
- CN6 始终协商为 P2P **GO**，竞品 X6878 为 GC
- 关闭蓝牙不能解决

## 根因结论
**模式 A（P2P 层）**：手机作为 GO 创建 P2P 组时，Kernel 报告 `Mgmt Frame TX Fail, Status: 3`，GC（电视盒子）未能加入，组形成失败。

**模式 B（RTSP 层）**：P2P 链路、四次握手、DHCP（192.168.49.188）均正常，手机 `MtkWifiDisplaySource` 已在 `192.168.49.1:7236` 监听，但对端 WFD Sink 未发起 RTSP TCP 连接，约 30s 超时。DHCP 后无 ARP 请求，说明对端网络栈未进入 WFD 业务阶段。待 MTK 确认 GO/GC 角色协商及 Sink 兼容性（ALPS11332661）。

## 排查步骤
1. 通过 `P2P-GROUP-FORMATION-FAILURE` 或用户感知投屏失败定位事件
2. 检查 wpa_supplicant：区分 P2P 层失败 vs P2P 成功
3. P2P 成功时检查：`AP-STA-CONNECTED`、`EAPOL-4WAY-HS-COMPLETED`
4. 检查 DHCP：`[p2p0.DHCP] Transmitting DhcpAckPacket` 是否分配 192.168.49.x
5. 检查 RTSP：`MtkNetworkSession: incoming connection from 192.168.49.x` 是否出现
6. 成功必有 `MtkWifiDisplaySource: We now have a client connected`；失败则仅有 `socket listen` 后超时 stop
7. Kernel 日志搜索 `Mgmt Frame TX Fail` 排查 P2P 层问题
8. 确认 P2P 角色：CN6 是否为 GO（`P2P-GROUP-STARTED p2p0 GO`）

## 关键日志
```
// 模式 B 失败 — P2P/DHCP 正常，无 RTSP 连接
06-02 10:24:19.226431  wpa_supplicant: P2P-GROUP-STARTED p2p0 GO ssid="DIRECT-TB-TECNO CAMON Slim 5G" freq=5240
06-02 10:24:19.822915  wpa_supplicant: p2p0: EAPOL-4WAY-HS-COMPLETED be:c7:da:eb:69:09
06-02 10:24:19.878870  MtkWifiDisplaySource: Bind to IP-port==>192.168.49.1:7236
06-02 10:24:20.649360  [p2p0.DHCP] Transmitting DhcpAckPacket ... netAddr: 192.168.49.188/24
（无 incoming connection，10:24:49 MtkWifiDisplaySource::stop）

// 模式 B 成功 — 对比
06-02 10:24:06.442686  MtkNetworkSession: incoming connection from 192.168.49.188:59854 (socket 11)
06-02 10:24:06.443429  MtkWifiDisplaySource: We now have a client (2) connected.

// 模式 A 失败 — P2P 组形成失败
06-02 10:20:44.892830  wpa_supplicant: P2P-GROUP-FORMATION-FAILURE
06-02 10:20:44.894276  wpa_supplicant: P2P-GROUP-REMOVED p2p0 GO reason=FORMATION_FAILED
[wlan] p2pDevFsmRunEventMgmtFrameTxDone: Mgmt Frame TX Fail, Status: 3
```

## TAG
- Miracast
- WFD
- 投屏
- P2P-GO
- P2P-GROUP-FORMATION-FAILURE
- RTSP超时
- MtkNetworkSession
- MtkWifiDisplaySource
- DHCP成功
- Mgmt Frame TX Fail
- CN6
- MTK平台
- ALPS11332661

## 相关案例
- CASE-003: 手机向PC分享图片/文档提示连接失败（P2P连接成功后DHCP失败）— 同为链路层成功、应用层失败，但失败层为 DHCP
- CASE-001: Windows PC接收端P2P冲突导致极速互传连接失败率高
