# CASE-039: Trusted Credentials 禁用导致系统 CA 不可信、WiFi Limited connection

## 基本信息
- **案例ID**: CASE-039
- **分类**: auth-failure
- **来源**: X6886OS16-290
- **创建时间**: 2026-10-03
- **匹配次数**: 0

## 现象描述
- 巴基斯坦 Overseas / Infinix Hot 60 Pro+（X6886），Android 16，`X6886-16.3.0.145SP08(OP004PF001AZ)`，MTK
- 升级后连 WiFi（现场为 SoftAP `Infinix GT 50 Pro`，BSSID `62:79:a4:85:01:cd`，5745 MHz）显示 **Limited connection**，上网异常
- 对照机 X6879 同 AP 约 7 分钟后 `+VALIDATED`，Probe `response=204`
- DUT：L2/4-way/DHCP 成功，RSSI 约 -42 dBm，网关 Ping 成功，无射频断连

## 根因结论

**系统 Trusted Credentials 中系统 CA 被 disable，信任锚缺失。公网证书（GeoTrust 等）仍被客户端判 `certificate_unknown`；HTTPS 探测失败 → `PARTIAL_CONNECTIVITY` → Limited connection。非 WiFi 驱动/射频问题。测试重新 enable Trusted Credentials 后恢复。**

本次问题现场 APLog **不能证明是用户当场手动关闭该开关**：无 Trusted Credentials 页面、无 KeyChain 禁用记录；禁用为持久状态，动作可发生在抓 log 之前。未看到 MDM 设备所有者。

机理链条：
1. Assoc + 4-way + DHCP（wlan0 `10.224.249.190`，GW `10.224.249.195`）成功
2. HTTP `connectivitycheck.gstatic.com/generate_204` 可返回 204；HTTPS `:443` 握手不完整
3. `WifiNetworkCheck: Probe result: not validated` + Ping 成功 → `+PARTIAL_CONNECTIVITY` → UI Limited connection
4. tcpdump 蜂窝 IP `10.209.98.181`：35×`certificate_unknown`、2×`access_denied`（如 `dialog-api.transsion-os.com`、`z-m-gateway.facebook.com`）
5. main_log：`Trust anchor for certification path not found` / `SSLHandshakeException`
6. 复测：Settings → Password & Security → System Security → Encryption & Credentials → Trusted Credentials，enable 被关项后问题解决

## 排查步骤

1. 排除射频：RSSI、assoc、4-way、DHCP、网关 Ping
2. 查 `Update capabilities`：`+PARTIAL_CONNECTIVITY` 且 `networkAddInterface` 为 `wlan0`
3. tcpdump 查 TLS Alert：`certificate_unknown` / `access_denied`；解析叶子证是否仍在有效期、是否公网 CA
4. main_log 搜 `Trust anchor for certification path not found`
5. 请测试检查 Trusted Credentials 是否有 disabled 项并全部 enable 后复测
6. **不要**仅凭本次 APLog 断言“用户刚点了关闭”；要证明操作需当时 Settings/KeyChain log 或机内 `cacerts-removed`

## 关键日志

```
13:19:56  CTRL-EVENT-CONNECTED  SSID=Infinix GT 50 Pro
13:19:56  networkAddInterface(114, wlan0)
13:20:06  WifiNetworkCheck: Probe result: not validated
13:20:06  WifiNetworkCheck: Ping result: {success=true, time=13ms}
13:20:14  Update capabilities for net 114 : +PARTIAL_CONNECTIVITY
13:20:14  Tile.TrWifiTile: secondaryLabel=Limited connection

Glide: SSLHandshakeException: Trust anchor for certification path not found.

tcpdump TLS Alert:
  certificate_unknown  SNI=dialog-api.transsion-os.com
    leaf CN=*.transsion-os.com  issuer=GeoTrust TLS ECC CA G1  (未过期)
  access_denied        SNI=z-m-gateway.facebook.com
```

## TAG
- 网络验证失败
- 部分连通PARTIAL_CONNECTIVITY
- 无互联网
- 证书信任
- Trust anchor
- certificate_unknown
- access_denied
- SSLHandshakeException
- Trusted Credentials
- Ping成功Probe失败
- SoftAP
- X6886
- 巴基斯坦
- MTK平台

## 建议措施

1. Trusted Credentials 将被 disable 的系统 CA **全部 enable**（已验证有效）
2. 同类 Limited connection：先查证书信任，再查门户/上游/驱动
3. 取证“谁关的开关”需单独抓操作时刻 log 或查 `cacerts-removed`

## 关联案例
- **CASE-029**：门户劫持导致 HTTPS 证书 mismatch（`SSLPeerUnverifiedException`）；本案是系统 CA 被禁用，证书本身合法
- **CASE-019**：Probe 失败导致无互联网/感叹号（探测失败表象类似，根因不同）

## 分析报告
- `AI-result/issues/X6886OS16-290/X6886OS16-290-analysis.md`
