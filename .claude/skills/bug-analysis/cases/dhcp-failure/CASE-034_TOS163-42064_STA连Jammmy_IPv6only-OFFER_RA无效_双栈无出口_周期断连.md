# CASE-034: CN6 STA 连对方热点 Jammmy 配网失败（RFC 8925 IPv6-only OFFER + RA 无效）

## 基本信息
- **案例ID**: CASE-034
- **分类**: dhcp-failure
- **来源**: TOS163-42064
- **创建时间**: 2026-07-10
- **匹配次数**: 0

## 现象描述
- TECNO CN6（Android 16 / HiOS 16.3.0 / MTK）作为 **STA** 连接对方手机热点 SSID「Jammmy」
- L2 关联 + 4-Way 成功，用户体感「连上但用不了 / 不 proceed」
- 21:30 后多次 **~18s 连断循环**，21:30 后 **0 次** `Wifi network validated`
- kernel：每轮 **DISCOVER → OFFER**，**0 REQUEST/ACK**
- dump-networking：每轮 `POST_DHCP arg=3`，Jammmy **0 次** `onNewDhcpResults`，LinkProperties **仅 fe80::/64**
- 断连均为 `locally_generated=1`（IpClient 18s PROVISIONING_TIMEOUT 后本机主动断连）

## 根因结论
**主因（热点侧）**：Jammmy 热点（`172.20.10.1`，疑似 iPhone 个人热点）按 **RFC 8925** 返回 **IPv6-only Preferred OFFER**（yiaddr=0.0.0.0 + DHCP Option 108 V6ONLY_WAIT=0），但不分配 IPv4；随后 **IPv6 RA 配置不完整**（Router Lifetime=0、PIO prefix `::`/lifetime=0），虽有 NAT64 prefix `64:ff9b::/96` 和 RDNSS，但 **无默认路由、无可用全局 IPv6 前缀** → **双栈无出口**。

**次因（CN6 策略）**：IpClient `mProvisioningTimeoutMs=18000` 在无可用 IP 时触发 STOP/断连；断连重连构成 RFC 8925 **network attachment event**，重置配网并再次 DISCOVER（仍带 opt108），形成 11 轮循环。

**CN6 协议栈**：行为 **符合 RFC 8925**（含 opt108 的 OFFER 不发 REQUEST；V6ONLY_WAIT=0 时本地 timer 应设为 MIN_V6ONLY_WAIT=300s）。非 DhcpClient 解析 bug。

**已排除**：密码错（0 WRONG_KEY）、AP 踢线（kernel reason=LOCALLY）、本机 SoftAP 干扰、Settings 扫网致断连、ONLINE_SCAN 导致无 REQUEST（POST_DHCP(3) 在 OFFER 后 5ms，先于 scan 72ms）。

## 排查步骤
1. 确认 L2：`CTRL-EVENT-CONNECTED` Jammmy、SAA Auth/Assoc 链正常
2. 检查 kernel DHCP：仅 DISCOVER→OFFER，无 REQUEST/ACK
3. 解析 dump-networking HEX：
   - DISCOVER opt55 含 **108**（CN6 声明支持 IPv6-only）
   - OFFER yiaddr=0 + opt108=0（`6C 04 00 00 00 00`）
   - POST_DHCP(3) 在 OFFER 后 ~5ms
4. 检查 IPv6：RS → RA，Router Lifetime=0、PIO 无效
5. 对齐 TIMEOUT：每轮 START→STOP 约 **18.17s**，与 `mProvisioningTimeoutMs: 18000` 一致
6. 对照成功场景：同 dump 中 19:27/20:27 连其他 AP 得 `172.20.30.122/24`，证明 CN6 DHCP 链路正常

## 关键日志

### dump-networking（21:35:07 样本轮，XID 0x16a07770）
```
2026-07-09T21:35:07.584  CMD_START Jammmy mProvisioningTimeoutMs:18000
2026-07-09T21:35:07.661  TX DISCOVER（opt55 含 108）
2026-07-09T21:35:07.711  RX OFFER yiaddr=0.0.0.0 opt108=0
2026-07-09T21:35:07.716  CMD_POST_DHCP_ACTION arg=3    # IPv4 路径结束
2026-07-09T21:35:08.386  TX IPv6 RS
2026-07-09T21:35:08.434  RX RA Router Lifetime=0, PIO ::
2026-07-09T21:35:08.447  onLinkPropertiesChange fe80::/64 only
2026-07-09T21:35:25.758  EVENT_PROVISIONING_TIMEOUT
2026-07-09T21:35:25.807  --- STOP ("Jammmy") ---
```

### kernel（21:35:07）
```
07-09 13:35:07.506  aisFsmSteps: [JOIN] -> [NORMAL_TR]
07-09 13:35:07.661  DHCP: Send DISCOVER, XID[0x16a07770]
07-09 13:35:07.711  DHCP: Recv OFFER, TransID 0x16a07770
07-09 13:35:07.783  mtk_cfg80211_scan -> ONLINE_SCAN    # 次要，非 REQUEST 缺失主因
07-09 13:35:25.874  mtk_cfg80211_disconnect reason=LOCALLY
```

### main（21:35:25 断连）
```
07-09 21:35:25.939  wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=ee:ec:3a:bc:a3:7b reason=3 locally_generated=1
```

## 报文要点（HEX 解析）

| 项目 | 值 |
|------|-----|
| STA MAC | da:c1:b9:1a:3d:fb |
| 热点 DHCP 服务器 | 172.20.10.1 / MAC 8e:08:aa:0c:eb:64 |
| OFFER yiaddr | 0.0.0.0 |
| OFFER opt108 | V6ONLY_WAIT=0（服务器未指定等待时长；客户端 SHOULD 本地设 MIN=300s） |
| OFFER DNS | 124.6.181.26, 124.6.181.25 |
| RA Router Lifetime | 0 |
| RA PIO | prefix_len=0, lifetime=0, prefix=:: |
| RA PREF64 | 64:ff9b::/96 |

## IPv6 RA 字段语义（RFC 4861）

OFFER 后 CN6 发 RS，收到 RA（源 `fe80::8c08:aaff:fe0c:eb64`），但 Router Lifetime 与 PIO 均无效，是 IPv6 路径失败的**核心断点**。

### Router Lifetime = 0 → 无 IPv6 默认路由

RA 报文头 **Router Lifetime**（秒）指示客户端是否将该 RA 源作为 **IPv6 默认路由器**：

| 值 | 语义 | 本案例 |
|----|------|--------|
| > 0 | 添加默认路由 `::/0 via fe80::8c08:aaff:fe0c:eb64` | — |
| **= 0** | **不要**把发送者当默认路由器 | Jammmy 实际值 |

即 **没有可用 IPv6 默认路由**，链外流量（含 NAT64 目标）无法转发。

### PIO Prefix Lifetime = 0 → 无 IPv6 地址前缀

**Prefix Information Option (PIO, opt3)** 负责 SLAAC 全局地址：

| PIO 字段 | Jammmy 值 | 含义 |
|----------|-----------|------|
| Prefix Length | 0 | 无效 |
| Prefix | :: | 空 |
| Valid / Preferred Lifetime | 0 | 前缀不可用 |

客户端无法获得全局 IPv6 地址，仅有 **fe80::/64** link-local。

### 矛盾：IPv6-only 信号 + 坏 RA

```
DHCP OFFER: yiaddr=0 + opt108 → 别用 IPv4，走 IPv6-only
CN6 RS    → 请求路由与前缀
iPhone RA : Router LT=0、PIO ::/0 → 无路由、无全局地址
          : PREF64 64:ff9b::/96、RDNSS fe80::... → 有线索但无法工作
CN6 结果  : LinkProperties 仅 fe80::/64，0 validated
```

NAT64 至少需要 **默认路由 + 可用 IPv6 源地址**；本案例两项均缺。

## 建议措施
1. **热点端（优先）**：确认对方蜂窝网正常；重启热点；iPhone 开「最大兼容性」；换普通路由器对比
2. **CN6 Framework（中优）**：IPv6-only OFFER 后 RA 无效 → fallback 重试 DHCP **不请求 opt108**
3. **MTK（低优）**：IPv6-only 转场期间 defer ONLINE_SCAN

## TAG
- STA连热点
- 关联成功
- L2成功IP失败
- RFC8925-IPv6only
- DHCP止于OFFER
- OFFER-yiaddr0
- Option108-V6ONLY_WAIT0
- 无REQUEST无ACK
- POST_DHCP(3)
- IPv6-RA无效
- RA-RouterLifetime0
- PIO无效
- NAT64-prefix无路由
- 双栈无出口
- PROVISIONING_TIMEOUT-18s
- locally_generated断连
- 无VALIDATED
- iPhone热点疑似
- CN6
- MTK平台
- Android16

## 相关案例
- CASE-003 - P2P 连接成功后 DHCP 失败（同为 DHCP 配网失败，但场景为 P2P 且含 APF/REQUEST 无 ACK 模式）
- CASE-015 - 已连接无法上网（同为「连上但用不了」，但根因为上行 TX 失效 + 信道争用）

## 分析报告
- `AI-result/issues/TOS163-42064/TOS163-42064-analysis.md`
