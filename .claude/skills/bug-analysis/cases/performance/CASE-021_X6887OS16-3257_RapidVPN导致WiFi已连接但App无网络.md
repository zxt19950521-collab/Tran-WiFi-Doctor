# CASE-021: Rapid VPN 干扰导致 Reception WiFi「已连接但无法上网」（关 VPN 后恢复，非 WiFi 缺陷）

## 基本信息
- **案例ID**: CASE-021
- **分类**: performance
- **来源**: X6887OS16-3257
- **创建时间**: 2026-06-25
- **匹配次数**: 0
- **参考文档**: https://transsioner.feishu.cn/docx/ST5MdtNfeoTRTMxOCMdctvDUnbf

## 现象描述
- 海外坦桑尼亚反馈：X6887 连接 **Reception** WiFi 后 Chrome/社交/YouTube 等全 App 无网络，同一 WiFi 下 **Infinix X6728B** 访问正常。
- 机型 TECNO X6887，Android 16 / HiOS 16.2.0（X6887-16.2.0.140SP05(OP005PF001AZ)），MTK 平台
- SSID `Reception`，BSSID `d8:32:14:2a:ad:15`，Tenda 5G AP；DHCP 192.168.2.192/24，网关/DNS 192.168.2.1 + 8.8.8.8
- 现场视频显示 WiFi 连接过程正常，但应用层表现为不可联网。
- **用户确认：关闭 Rapid VPN 后网络恢复正常。**
- 关键：WiFi 关联/DHCP/**VALIDATED** 均正常；kernel/tcpdump 显示四次握手、DHCP、ARP、系统 DNS 探测正常；业务层大量 DNS 失败。

## 根因结论
**第三方 VPN（Rapid VPN / Shadowsocks）与 Reception WiFi 路由/DNS 冲突，tun 隧道分流导致局域网及外网不可达；关闭 VPN 后恢复。非 WiFi 驱动/网络栈/AP 故障。**

机理链条：
1. 设备安装 **Rapid VPN**（`com.rapidconn.android`，`com.github.shadowsocks.bg.VpnService`，`libtun2socks.so`）
2. **14:36:22** VPN 连接，**14:36:29** Reception WiFi DHCP 成功 → VPN + WiFi 叠加约 5 分钟
3. VPN 建立 netId 100（`VPN:com.rapidconn.android`），流量经 tun0 分流；局域网网关 192.168.2.1 及 DNS 被错误劫持
4. 业务层：`UnknownHostException` / `getaddrinfo(): No address associated with hostname` ≥1112 次；系统仍可能显示 VALIDATED（探测路径与 App DNS 路径不同）
5. **14:41:45** 用户手动关闭 VPN（`Vpn disconnect` + `foreground_service_stop`，同秒 `panel_open` 下拉通知栏）
6. WiFi 链路侧：SAA Auth/Assoc、EAPOL M1—M4、DHCP ACK、ARP Rsp、系统 DNS TX/RX 均正常
7. main_log 中 `WifiNetworkCheck` Ping `success=false` 仅 2—6ms（非弱信号 1s timeout）；公网 IPv4 ICMP probe 失败
8. **用户确认关闭 VPN 后恢复** → 根因闭环

## 排查步骤
1. **先查 VPN（首要）**：在 `events_log` / `sys_log` 搜索
   - `am_foreground_service_start/stop` + `VpnService`
   - `TranGriffin/Vpn: Vpn disconnect`
   - `com.rapidconn.android` / `libtun2socks.so` / `shadowsocks`
2. **确认 VPN 与 WiFi 时间重叠**：对照 IpClient dump / `dump-networking` 中 DHCP 时间与 VPN 连接时段
3. **确认问题窗口默认网络**：`networkCreate(... vpnType: -1)` + `dump-networking` 中 `Active default network` 是否 `NOT_VPN`
4. **排除 WiFi 链路**：kernel 查 `saaFsmSteps`、EAPOL M1—M4、DHCP/ARP/DNS TX/RX
5. **业务面 DNS**：main_log 搜 `UnknownHost` / `Could not contact DNS servers` / `msys`
6. **竞品/同 AP 对比**：第二台无 VPN 手机是否同 AP 正常（本案 X6728B 全通）
7. **用户验证**：关闭 VPN 后是否恢复（本案已确认）

## 关键日志
```
// VPN 连接（events_log）
06-18 14:36:24.710  am_foreground_service_start: com.rapidconn.android/...VpnService
06-18 14:36:25.xxx  auditd: comm="libtun2socks.so"

// VPN 断开（用户手动）
06-18 14:41:45.320  am_foreground_service_stop: ...VpnService, STOP_FOREGROUND
06-18 14:41:45.434  TranGriffin/Vpn: Vpn disconnect
06-18 14:41:45.829  network=[type: VPN[], state: DISCONNECTED/DISCONNECTED]

// WiFi 正常、默认网非 VPN（main_log + dump-networking）
06-18 14:43:27.650  netd: networkCreate(... networkType: PHYSICAL, vpnType: -1)
06-18 14:44:19 dump: Active default network: 102, Capabilities: ... NOT_VPN ... VALIDATED

// 关联与四次握手成功（kernel，+3h 对齐 main）
11:43:27.327 statsParsePktInfo: <RX> EAPOL: key, M1
11:43:27.351 statsParsePktInfo: <TX> EAPOL: key, M4
11:43:27.826 statsParseUDPInfo: <RX> DHCP: Recv ACK

// 业务层 DNS 失败
06-18 14:42:29.393  msys: getaddrinfo(): No address associated with hostname
06-18 14:43:52.710  msys: Could not contact DNS servers, timeouts: 0

// WiFiNetworkCheck ping 很快失败（main_log）
14:43:38.177 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=4ms}

// 公网 IPv4 ICMP probe 失败（main_log）
14:43:28.164 NetworkPingMonitor: ICMP probe failed for 1.1.1.1: Execution failed

// 用户闭环
客户确认使用 VPN；关闭 VPN 后网络正常。
```

## 易错点
- **`res_doh_send: 468` 不是错误码**：468 为 HTTPS 响应体字节数；日志中亦有 `doQuery: rcode=0` 成功记录，勿误判为 Private DNS opportunistic 回退缺陷
- **VALIDATED 与 App 无网可并存**：系统 HTTP 探测通过 ≠ 通用 DNS/业务流量正常；VPN 分流时更易出现此分裂
- **ICMPv6 RS/邻居发现 ≠ 公网可用**：链路本地协议，WiFi 一连即发，不能证明 App 业务路径正常
- **VPN 断开后日志仍见 DNS 失败**：可能为 tun 拆除残留；**以用户关 VPN 后是否恢复为准**

## TAG
- 已连接无法上网
- connected but not working
- VPN干扰
- 第三方VPN
- Rapid VPN
- Shadowsocks
- VpnService
- libtun2socks
- tun0分流
- DNS解析失败
- UnknownHost
- VALIDATED
- WiFi未断开
- 非WiFi缺陷
- 关VPN恢复
- 对比机正常
- Tenda AP
- 办公WiFi
- X6887
- 坦桑尼亚
- IPv4路径异常
- 公网ICMP失败
- DHCP正常
- ARP正常
- 四次握手成功
- MTK平台
- 海外反馈

## 建议措施
1. **用户侧（已验证）**：关闭或卸载 Rapid VPN 后再连办公 WiFi
2. **若需保留 VPN**：开启 **绕过局域网**（Bypass LAN / 192.168.0.0/16），避免劫持网关 DNS
3. **工单流转**：标注 **Non-issue / 用户环境**，无需转 WiFi 驱动或网络栈
4. 现场优先让用户关闭 VPN/代理/私有 DNS 后复测；若恢复则按第三方 VPN 问题闭环
5. 对 `Ping result: {success=false, time=几ms}` 与弱信号 `time=1000ms` timeout 区分：前者更偏 VPN/路由快速失败

## 数据局限
- main log 仅覆盖 14:42:28—14:44:20；首次 DHCP 14:36:29 来自 IpClient dump
- Rapid VPN 连接态以 events_log VpnService 为准；最终闭环依赖用户确认关 VPN 后恢复
- 无完整 VPN 路由表/NetworkAgent 细节

## 相关案例
- **CASE-015（OS162-41328）**：同为「已连接无法上网」+ DNS 失败 + WiFi 未断开。区别：CASE-015 主因为 **上行 TX path 失效 + ch11 同频争用**，需重启整机；本案为 **第三方 VPN**，关 VPN 即恢复。
- **CASE-020（TOS163-38141）**：同为 App 无网表象。区别：CASE-020 是弱信号、PER/ACK fail、Ping 1s timeout；本案 Ping 几 ms 快速失败且关 VPN 恢复。
- **CASE-012（TOS163-35222）**：同为业务层报无网但系统 WiFi 正常。区别：CASE-012 为 **Shopee 应用弱网库误报**；本案有明确 VpnService 日志。
- **CASE-018（TOS163-37551）**：同为 **非 WiFi 驱动故障**。区别：CASE-018 为 TranEngine 主动关 WiFi；本案 WiFi 保持连接，VPN 干扰数据面。
- 鉴别要点：**是否安装/开启 VPN** → 搜 VpnService；**关 VPN 是否恢复**；**竞品同 AP 是否正常**。
