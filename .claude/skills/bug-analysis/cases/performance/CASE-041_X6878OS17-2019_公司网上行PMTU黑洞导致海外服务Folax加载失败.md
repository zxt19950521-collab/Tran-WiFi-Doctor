# CASE-041: 公司网上行 PMTU 黑洞导致海外服务（Folax）加载失败，WiFi 强信号且系统已验证

## 基本信息
- **案例ID**: CASE-041
- **分类**: performance
- **来源**: X6878OS17-2019（粉丝反馈 796486637，TagLog / Normal / Subsyslog，含 tcpdump 与 DNS 记录）
- **创建时间**: 2026-10-14
- **匹配次数**: 0

## 现象描述
- 粉丝反馈：连公司 WiFi `Transsion_Mobile`“信号很差、经常连不上网络”，怀疑手机本身有问题
- 机型 Infinix X6878（XOS 17 / Android 17，高通 wcn6450），5G ch161
- 状态栏 WiFi 正常、无感叹号；Folax（`com.transsion.aivoiceassistant`）一直 “Loading content...”
- 用户在通知栏关 WiFi 再打开（14:22:25 → 14:22:30），重连后问题依旧

## 根因结论

**公司网出口到海外的上行路径 MTU < 1500，且中间设备不回 ICMP “需要分片”、不做 TCP MSS 钳制。对端通告 MSS 1460 时，手机发出的 1500 字节 DF 上行包被静默丢弃，TCP 连接卡死，约 14 秒后被服务器关闭。** 另外该网络访问 Google 443 的 SYN 无任何响应。

判定为网络侧（非手机射频/驱动）的依据：
- 无线链路正常：关联 RSSI -52 ~ -44 dBm（均值 -47.3），SNR 均值 48.7 dB，PHY 均值 142 Mbps（HE MCS 11）；系统探测 13 次全部成功
- tcpdump（14:26:07 ~ 14:26:59）：对端 MSS ≥ 1452 的 29 条海外连接，41 个 ≥1450 字节上行包**被确认 0 个**；同连接里的小包基本都被确认，对端还会 SACK 排在大包后面的小包
- 对端 MSS 1360 的海外服务器（`ire-dsu.shalltry.com` 47.254.145.126）上行大包 7/7 正常
- 下行 1500 字节包能正常收到；ICMP ping 网关、1.1.1.1、8.8.8.8、87.119.3.37 都有回包
- 抓包中无 ICMP Type 3（目的不可达 / 需要分片）
- Folax 的 TLS 握手能完成（收到 ServerHello），排除按 SNI/域名封锁

为什么系统显示“已连接、可上网”：
- 联网检测走国内服务器 `connectivitycheck.gstatic.cn`、`conn5.coloros.com`，请求很小 → `+VALIDATED`
- Folax 自身网络探测也是小包（`reachability=REACHABLE avgRtt=44ms`）
- 两者都不发 1500 字节上行包，检测不到黑洞

手动关开 WiFi 是用户在加载失败后的反应（`reason=3 locally_generated=1`），重连仍走同一出口，不能解决。

已排除：
- **弱信号 / 射频**：见上述链路指标
- **DNS**：私有 DNS `223.5.5.5:853` 正常，海外域名解析结果正常
- **域名封锁 Folax**：TLS 握手成功，服务器 SACK 后续小包

未闭环：
- 黑洞具体位置（公司出口、国际专线隧道或运营商出口）需网络侧确认
- 仅有公司网数据，需移动数据对比确认“仅公司网出现”

## 排查步骤
1. **先排除射频**：host_driver `wlan_hdd_update_rssi` / `wlan_hdd_update_rate_info` 统计关联 RSSI、SNR、MCS；`WifiNetworkQuality: record probe result` 看探测
2. **核对验证服务器归属**：`net/dns/dns_info_record*.txt` 中 `android.uid.networkstack` 解析的域名（国内 → VALIDATED 不代表海外可达）；业务 App 的域名是否在海外
3. **tcpdump 逐连接**：SYN-ACK 通告的 MSS；上行数据段按 IP 包长分档统计是否被 ACK/SACK；同一 seq 的 1500 字节 DF 包是否指数退避重传；是否有 ICMP Type 3
4. **对照**：找对端 MSS ≤ 1360 的海外连接是否正常；下行大包是否正常
5. **应用日志**：`unexpected end of stream`、`SocketTimeoutException`、WebSocket `timeout`，确认时间与抓包一致
6. **勿误判**：`reason=3 locally_generated=1` 先核对是否用户手动关 WiFi（`Tile.TrWifiTile: handleClick`）；系统 VALIDATED 不能证明海外业务可达

## 关键日志

```
// tcpdump：Folax -> bus-ie.aibotplatform.com (87.119.3.37:443)，本地端口 47650
14:26:11.703 IN  S.   iplen=60   MSS=1460
14:26:11.782 IN  .P   iplen=308  tls_type=22 hs=2            <- ServerHello，握手成功
14:26:11.795 OUT .P   iplen=2948 DF len=2896 tls_type=23      <- 上传请求（GSO，2×1448）
14:26:11.957 IN  .    iplen=64   (ACK 停在 672，带 SACK)       <- 后面的 526B 小包已到
14:26:11.957 ~ 14:26:21.030 OUT iplen=1500 DF seq=672 len=1448 重传 6 次（0.3/0.6/1.2/2.4/4.6s）
14:26:25.775 IN  .F                                           <- 服务器约 14s 后放弃
14:26:25.837 IN  R

// 对照：ire-dsu.shalltry.com (47.254.145.126:443)，MSS 1360，正常
14:26:10.895 IN  S.   iplen=60   MSS=1360
14:26:11.483 OUT .P   iplen=1179 tls_type=23
14:26:11.695 IN  .P   iplen=302  tls_type=23

// Google：172.217.112~119.4:443，25 条连接只有 SYN，0 个 SYN-ACK

// Folax 应用层
10-12 14:22:44.310759 RetryDetectInterceptor: [Ella] Retry detected: attempt=1, phase=response, reason=IOException(unexpected end of stream on https://bus-ie.aibotplatform.com/...)
10-12 14:22:45.241607 L.Http  : [Ella] <-- HTTP FAILED: java.net.SocketTimeoutException: timeout
10-12 14:23:00.234155 NetSDK_WsConnection: [NetSDK]onFailure ... url:wss://bus-ie.aibotplatform.com/ws/assistant/agent/call reason:WebSocket failure:, Exception: timeout

// 系统验证走国内
2026-10-12 14:22:29 DnsEvent(108, connectivitycheck.gstatic.cn, 120.232.233.171 ..., pkName=android.uid.networkstack:1073
10-12 14:22:29.999305 ConnectivityService: Update capabilities for net 108 : +VALIDATED

// 用户手动关开 WiFi（结果，非原因）
10-12 14:22:25.742540 Tile.TrWifiTile: handleClick wifiEnabled=true expectDisabled=true
10-12 14:22:25.808007 wpa_supplicant: wlan0: CTRL-EVENT-DISCONNECTED bssid=14:84:77:26:7b:80 reason=3 locally_generated=1
```

## 统计数据

| 上行 IP 包长 | 被确认 | 未被确认 |
|------|------|------|
| < 1000 字节 | 120 | 6（连接关闭前最后一段） |
| 1000 ~ 1399 字节 | 8 | 0 |
| ≥ 1450 字节，对端 MSS 1360 | 7 | 0 |
| ≥ 1450 字节，对端 MSS ≥ 1452 | 0 | 41 |

| Folax 报错（14:22 ~ 14:27，13:29 另有 5 次） | 次数 |
|------|------|
| `unexpected end of stream` | 61 |
| `SocketTimeoutException` | 17 |
| WebSocket failure | 5 |

## 解决建议
1. **公司网 IT**：出口网关 / 防火墙 / 国际专线开启 TCP MSS 钳制（`clamp-mss-to-pmtu` 或固定 1360），或放行 ICMP Type 3 Code 4；可用 `ping -f -l 1472 87.119.3.37` 与 `-l 1300` 对比确认
2. **对比验证**：同机切移动数据或其他 WiFi 打开 Folax
3. **服务端规避（可选）**：海外业务服务器 SYN-ACK 通告 MSS 降到 1360，或开启 PLPMTUD
4. **手机侧**：无需修改射频/驱动；`net.ipv4.tcp_mtu_probing=1` 可作为系统级规避，需单独评估

## TAG
网络侧限制, 上行PMTU黑洞, MSS未钳制, 大包丢小包通, DF重传无ACK, 无ICMP需要分片, 海外服务器访问失败, Google不可达, SYN无响应, 网络已验证可上网, 验证服务器在国内, unexpected end of stream, SocketTimeoutException, Folax, aibotplatform, 应用加载失败, 强信号, 5G频段, 用户手动开关WiFi, 公司网, X6878, wcn6450, 高通平台, 粉丝反馈

## 相关案例
- CASE-026：公司专网已连接无互联网（原因是网关 ARP 无响应，L2/L3 不通）
- CASE-021：VALIDATED 但业务失败（原因是第三方 VPN）
- CASE-017：同机型 X6878 / wcn6450 强信号下应用加载慢（应用解码问题），可佐证射频正常
