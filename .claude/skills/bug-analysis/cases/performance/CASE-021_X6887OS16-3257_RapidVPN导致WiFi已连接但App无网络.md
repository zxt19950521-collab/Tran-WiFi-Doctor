# CASE-021: Rapid VPN 导致 WiFi 已连接但 YouTube 等 App 无网络（WiFi 链路正常）

## 基本信息
- **案例ID**: CASE-021
- **分类**: performance
- **来源**: X6887OS16-3257
- **创建时间**: 2026-06-25
- **匹配次数**: 0
- **参考文档**: https://transsioner.feishu.cn/docx/ST5MdtNfeoTRTMxOCMdctvDUnbf

## 现象描述
- 海外坦桑尼亚反馈：X6887 连接 WiFi 后 YouTube 等 App 无网络，同一 WiFi 下其他手机访问正常。
- 现场视频显示 WiFi 连接过程正常，但应用层表现为不可联网。
- 一线确认客户使用过 Rapid VPN，关闭 VPN 后网络恢复正常。
- 关键：kernel log 和 tcpdump 均显示 WiFi 关联、四次握手、DHCP、ARP、DNS 正常，问题不在 WiFi 链路层。

## 根因结论
**WiFi 链路和基础 IP 网络正常，应用无网络由客户侧 VPN/代理链路影响导致。Rapid VPN 可能接管或改写默认路由/IPv4 流量，使 YouTube 等主要使用 IPv4 的 App 访问失败；关闭 VPN 后恢复，故本案应按第三方 VPN/网络代理问题处理，非 WiFi 驱动/AP/射频问题。**

机理链条：
1. WiFi 关联成功：SAA 状态机完成 Auth/Assoc。
2. WPA 四次握手成功：kernel 看到 EAPOL M1/M2/M3/M4 完整收发。
3. DHCP 成功：STA 发 DHCP REQUEST，收到 DHCP ACK。
4. ARP 成功：STA 向网关发 ARP Req，收到网关 ARP Rsp。
5. Android 联网检测相关 DNS 正常：多笔 DNS TX 后均有 RX 响应。
6. main_log 中 WiFiNetworkCheck 的 `Ping result` 持续 `success=false`，虽然耗时只有 2~6ms，说明不是无线层高时延，而是探测结果判定/上层网络路径失败。
7. tcpdump/main_log 显示 ICMPv6 Router Solicitation/邻居发现可通，但公网 IPv4 ICMP probe 全部失败；多数 App 仍主要依赖 IPv4/HTTPS 路径，因此表现为 YouTube 等 App 无网络。
8. 日志存在 Rapid VPN 启动组件痕迹；一线联系客户确认使用 VPN，关闭 VPN 后恢复，最终闭环为 VPN 导致。

## 排查步骤
1. 先排除 WiFi 链路问题：
   - kernel 查 `saaFsmSteps` 是否完成 Auth/Assoc。
   - 查 EAPOL M1/M2/M3/M4 是否完整。
   - 查 DHCP REQUEST/ACK、ARP Req/Rsp、DNS TX/RX 是否正常。
2. 区分系统联网检测 DNS 与业务 App 网络：
   - 文档中 DNS 主要是 Android 系统联网检测，不等价于 YouTube/Facebook 等业务 App 的 HTTPS 请求成功。
   - DNS 正常只能说明基础解析路径可通，不能证明 VPN 后的 IPv4/HTTPS 业务路径可通。
3. 查 main_log 的 `WifiStatistics:WifiNetworkCheck`：
   - `Ping result: {success=false, time=2~6ms}` 这类“很快失败”不符合弱信号/空口重传导致的 1s timeout，更像上层路径/策略直接失败。
4. 查 IPv4/IPv6 差异：
   - ICMPv6 Router Solicitation/邻居发现属于链路本地自动协议，WiFi 一连接 Android 就会发，不能代表公网业务可用。
   - 公网 IPv4 ICMP probe 到 `1.1.1.1`、`8.8.8.8`、`9.9.9.9` 全部失败，说明业务常用 IPv4 路径异常。
5. 查 VPN/代理痕迹：
   - 搜 VPN 包名、启动组件、VPN service、默认网络/VpnNetworkAgent 等。
   - 本例出现 `com.rapidconn.android` / Rapid VPN 启动组件；客户确认关闭 VPN 后恢复。

## 关键日志
```
// 关联与四次握手成功（kernel）
11:43:27.297 saaFsmSteps: [SAA]TRANSITION: [AA_IDLE] -> [SAA_SEND_AUTH1]
11:43:27.306 saaFsmSteps: [SAA_WAIT_AUTH2] -> [SAA_SEND_ASSOC1]
11:43:27.327 statsParsePktInfo: <RX> EAPOL: key, M1
11:43:27.342 statsParsePktInfo: <TX> EAPOL: key, M2
11:43:27.349 statsParsePktInfo: <RX> EAPOL: key, M3
11:43:27.351 statsParsePktInfo: <TX> EAPOL: key, M4

// DHCP 成功（kernel）
11:43:27.799 statsParseUDPInfo: <TX> DHCP: Send REQUEST
11:43:27.826 statsParseUDPInfo: <RX> DHCP: Recv ACK

// ARP 网关可达（kernel）
11:43:27.949 statsParseARPInfo: <TX> ARP Req ... TAR MAC/IP[00:00::::00]/[192...1]
11:43:27.955 statsParseARPInfo: <RX> ARP Rsp ... SRC MAC/IP[d8:32::::10]/[192...1]

// DNS 有请求有响应（kernel，系统联网检测相关）
11:43:28.019 statsParseDNSInfo: <TX><IPv4> DNS: TransID[0x0e28]
11:43:28.022 statsParseDNSInfo: <RX><IPv4> DNS: TransID[0x0e28]
11:43:28.029 statsParseDNSInfo: <TX><IPv4> DNS: TransID[0x4284]
11:43:28.031 statsParseDNSInfo: <RX><IPv4> DNS: TransID[0x4284]

// WiFiNetworkCheck ping 很快失败，不像空口弱信号导致的 1s timeout（main_log）
14:43:38.177 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=4ms}
14:43:48.182 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=3ms}
14:43:58.187 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=4ms}
14:44:08.189 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=6ms}
14:44:18.187 WifiStatistics:WifiNetworkCheck: Ping result: {success=false, time=2ms}

// 公网 IPv4 ICMP probe 失败（main_log）
14:43:28.164 NetworkPingMonitor: ICMP probe failed for 1.1.1.1: Execution failed
14:43:28.644 NetworkPingMonitor: ICMP probe failed for 9.9.9.9: Execution failed
14:43:28.865 NetworkPingMonitor: ICMP probe failed for 8.8.8.8: Execution failed
14:43:30.635 NetworkPingMonitor: ICMP probe failed (Execution failed), fallback to HTTP probe

// VPN 使用痕迹（main_log / Launcher）
14:42:56.308 MostUsedAppsModel:
  targetComponent=ComponentInfo{com.rapidconn.android/com.rapidconn.android.ui.activity.Splash2Activity}
  title=Rapid VPN

// 一线闭环
客户确认使用 VPN；关闭 VPN 后网络正常。
```

## TAG
- WiFi已连接但App无网络
- connected but app no internet
- 非WiFi问题
- VPN影响
- Rapid VPN
- IPv4路径异常
- 公网ICMP失败
- DNS正常
- DHCP正常
- ARP正常
- 四次握手成功
- ICMPv6链路本地正常
- YouTube无网络
- 第三方App无网络
- MTK平台
- 海外反馈

## 建议措施
1. 现场优先让用户关闭 VPN/代理/私有 DNS/网络加速器后复测 YouTube、浏览器和系统联网检测。
2. 若关闭 VPN 后恢复，可按第三方 VPN/网络代理问题闭环，不建议转 WiFi 驱动/AP/RF。
3. 若仍复现，补充对比：
   - `ip route` / `dumpsys connectivity` / VPN NetworkAgent 状态；
   - tcpdump 中业务 App 的 IPv4/IPv6 HTTPS 请求路径；
   - WiFi 下公网 IPv4 ping、HTTP probe、DNS 查询是否都失败。
4. 分析时不要把 ICMPv6 Router Solicitation/邻居发现误判为“公网 IPv6 可用”；它只是链路本地协议，不能证明 App 业务路径正常。
5. 对 `Ping result: {success=false, time=几 ms}` 要和弱信号下 `time=1000ms` timeout 区分：前者更偏上层策略/路由/VPN 快速失败，后者更可能是链路时延/丢包。

## 数据局限
- 文档记录未给出完整 tcpdump 内容，仅摘录了关键结论和日志片段。
- Rapid VPN 是否实际处于连接态，日志中只直接看到启动组件；最终依据是一线确认“关掉 VPN 后网络正常”。
- 未提供 VPN 路由表/NetworkAgent 细节，无法进一步区分是默认路由、DNS、代理还是 IPv4 转发策略导致。

## 相关案例
- **CASE-015（OS162-41328）**：同为 WiFi 已连接但无法上网。区别：CASE-015 有 ACK/RTS fail、PER、DNS 失败等 WiFi/空口侧证据；本例 WiFi 链路、DHCP、ARP、DNS 正常，最终为 VPN 导致。
- **CASE-020（TOS163-38141）**：同为 App 加载/无网络表象。区别：CASE-020 是弱信号、10/10Mbps、PER/ACK fail 与 Ping 1s timeout；本例 Ping 几 ms 快速失败且关闭 VPN 后恢复。
- **CASE-012（TOS163-35222）**：同涉及第三方 App 网络表现与系统网络状态不一致。区别：本例有明确 Rapid VPN 外部因素闭环。
