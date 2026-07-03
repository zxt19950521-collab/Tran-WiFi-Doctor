# CASE-026: R&D 专网网关 ARP 无响应导致「已连接无互联网」（L2/ DHCP 正常，同机 R&D-Test 正常）

## 基本信息
- **案例ID**: CASE-026
- **分类**: disconnect
- **来源**: X6725BOS16-200
- **创建时间**: 2026-07-03
- **匹配次数**: 0

## 现象描述
- 孟加拉 STR5：X6725B 连接研发 Wi-Fi **R&D**（Cambium AP，WPA-PSK）后状态栏显示 **「Connected, no internet」**，网页/App 不可用
- 同环境对比机 REDMI Note 15 5G 正常；工单标注 **单机问题**（SN `14569552W000016`），**重启后恢复**
- 机型 X6725B，Unisoc/SPRD 平台，HiOS **X6725B-16.3.0.046**
- 问题时间 **2026-07-02 14:39:50 ~ 14:41:30**（扫码连 R&D 约 14:39:50）
- **WiFi L2 正常**：关联 + 4-way 成功；**非**密码错误、非 deauth 踢线

## 根因结论

**L2 关联与 DHCP 均成功，但默认网关 `192.168.20.1` 对客户端 ARP 零响应，导致 `NUD_FAILED` / `LOST_PROVISIONING`，NetworkMonitor 无法 `+VALIDATED`，系统显示「已连接无互联网」。问题专属于 R&D SSID 所在 L3 网络，非 DUT WiFi 栈整体故障。**

机理链条：
1. 连 **R&D**（BSSID `fc:11:65:57:bf:30`）后 DHCP 分配 **`192.168.21.163`**（`192.168.20.0/23`），默认路由 → `192.168.20.1`
2. **tcpdump**：`192.168.21.163 → 192.168.20.1` **113 次 ARP Request、0 次 Reply**
3. **main log**：`IpReachabilityMonitor` 连续 `192.168.20.1,NUD_FAILED`（73 条）→ `LOST_PROVISIONING`（21 次）→ `validated=false`
4. Probe/Ping/DNS TLS 全部超时（网关不可达，非单独 DNS 问题）
5. **同机同 tcpdump 对比**：约 **14:39:27** 连 **R&D-Test** 时 `192.168.50.243 → 192.168.50.1` **ARP 有 Reply**，`14:39:28` **`+VALIDATED`** → 排除整机网络栈损坏
6. R&D 使用 **随机 MAC** `f2:24:bf:dc:7f:0d`；DHCP 经 Relay **`172.16.86.225`**（非 R&D-Test 的直连 `192.168.50.1`）；DHCP 还下发跨网段 DNS **`192.168.200.31`**，需 AP 侧核对

## 同机对比（核心证据）

| 对比项 | R&D-Test（~14:39:27）✅ | R&D（~14:39:54）❌ |
|--------|------------------------|-------------------|
| BSSID | `a0:04:60:da:ab:fa` | `fc:11:65:57:bf:30` |
| 客户端 MAC | `7e:7c:0a:20:60:39` | `f2:24:bf:dc:7f:0d`（随机 MAC） |
| DHCP IP | `192.168.50.243` | `192.168.21.163` |
| 网关 | `192.168.50.1` | `192.168.20.1` |
| DHCP Server | `192.168.50.1` | `172.16.86.225`（Relay） |
| ARP | 1 REQ + **1 REP** | 113 REQ + **0 REP** |
| 验证 | `+VALIDATED` | 全程 `validated=false` |

## 排查步骤

1. **排除 L2**：`wpa_supplicant` 有 `Associated` + `Key negotiation completed`，无 `DISCONNECTED reason=17/15`
2. **确认 DHCP 已分配 IP**：tcpdump 查 DHCP OFFER/ACK 的 `yiaddr`；本案 **`192.168.21.163`** 已分配
3. **查网关 ARP（tcpdump /dec  decisive）**：
   - 过滤 `arp`，看客户端 IP → `192.168.20.1` 是否有 **Reply**
   - 本案：**仅 Request，无 Reply**
4. **查 main log NUD**：
   - `IpReachabilityMonitor` + `192.168.20.1,NUD_FAILED`
   - `LOST_PROVISIONING` / `NUD_ORGANIC_FAILED_CRITICAL`
   - `UnisocExtDataController: isNudFailedActually`
5. **查 validated**：`ConnectivityService: +VALIDATED` 是否出现；`SysUI NetworkRateController: validated=false`
6. **同机对比 SSID**：若另一 SSID（如 R&D-Test）ARP 正常且 `+VALIDATED` → 指向 **AP/专网配置**，非 DUT 硬件
7. **注意 MAC 随机化**：R&D 与 R&D-Test 可能用不同 MAC，AP ACL/隔离需按实际 MAC 查
8. **核对 DHCP Option**：网关、DNS（本案 DNS 含 `192.168.200.31` 与 `192.168.20.x` 不同网段）、Relay 地址

## 关键日志

```
// L2 正常（main_log）
07-02 14:39:54.560  Associated with fc:11:65:57:bf:30
07-02 14:39:54.579  WPA: Key negotiation completed [PTK=CCMP GTK=CCMP]

// L3 路由下发但网关 NUD 失败（main_log）
07-02 14:39:54.778  networkAddRouteParcel(109, 0.0.0.0/0 → 192.168.20.1)
07-02 14:39:54.925  UnisocExtDataController: isNudFailedActually: start for wlan0, 192.168.20.1
07-02 14:39:57.124  IpClient.wlan0: 192.168.20.1,NUD_FAILED
07-02 14:39:57.124  IpReachabilityMonitor: FAILURE: LOST_PROVISIONING, NUD_ORGANIC_FAILED_CRITICAL

// R&D-Test 对比：ARP 正常 + VALIDATED（main_log + tcpdump）
07-02 14:39:27.201  Associated with a0:04:60:da:ab:fa  (R&D-Test)
07-02 14:39:28.434  ConnectivityService: Update capabilities for net 108 : +VALIDATED
// tcpdump +13.1s:
//   ARP REQ 192.168.50.243 → 192.168.50.1
//   ARP REP 192.168.50.1 → 192.168.50.243  sha=48:a9:8a:bb:e8:2d

// R&D 专网：DHCP 有 IP 但网关 ARP 无响应（tcpdump +40.4s）
//   DHCP OFFER yiaddr=192.168.21.163 mac=f2:24:bf:dc:7f:0d srv=172.16.86.225
//   ARP REQ 192.168.21.163 → 192.168.20.1 ×113，无 Reply
```

## TAG
- 已连接无互联网
- Connected no internet
- NUD_FAILED
- LOST_PROVISIONING
- 网关不可达
- ARP无响应
- 网关ARP失败
- L2正常L3失败
- DHCP正常
- validated=false
- NetworkProbe超时
- IpReachabilityMonitor
- UnisocExtDataController
- SPRD平台
- Unisoc
- ylog
- 随机MAC
- DHCP Relay
- 专网SSID
- Cambium AP
- 同机对比SSID
- 重启恢复
- 单机问题
- tcpdump实锤

## 建议措施
1. **AP/网络侧（优先）**：Cambium R&D SSID 核对 DHCP 网关/DNS/Relay/VLAN；查 `192.168.20.1` 是否与客户 `192.168.21.x` 同广播域；查客户端隔离/MAC ACL 是否拦截随机 MAC `f2:24:bf:dc:7f:0d`
2. **复测抓包**：DUT + 对比机同连 R&D，同步 tcpdump + AP 侧 ARP 表
3. **Framework（次要）**：Unisoc `IpReachabilityMonitor` 切换 SSID 后仍监视旧网关 `192.168.20.1` 的残留问题；结合「重启恢复」查邻居表是否需清理

## 关联案例
- **CASE-019**（部分）：同为 Probe 失败 / `validated=false` / 感叹号；本案 **无 SSID 乒乓**，根因在 **网关 ARP 无响应** 而非 gstatic Probe 触发切网
- **CASE-015**（对比）：同为「已连接无法上网」；CASE-015 为 MTK **上行 TX 失效 + ch11 争用**，本案 L2 正常、PER 无异常，tcpdump 显示 **纯网关 ARP 失败**
- **CASE-021**（对比）：同为 App 无网表象；CASE-021 为 **第三方 VPN** 干扰，本案无 VPN，关网无效，需 AP 侧排查

## 来源报告
- Jira: X6725BOS16-200
- 分析报告: `AI-result/issues/X6725BOS16-200/X6725BOS16-200-analysis.md`
