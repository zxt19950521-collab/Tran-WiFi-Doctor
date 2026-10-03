# X6886OS16-290 Limited connection 分析报告

**测试时间**：2026-09-30 13:19~13:20（巴基斯坦本地，问题时间约 1:23 PM）  
**测试设备**：Infinix Hot 60 Pro+（X6886），Android 16，版本 X6886-16.3.0.145SP08(OP004PF001AZ)  
**测试文件**：`AI-result/issues/X6886OS16-290/logs/extracted/Wifi -x6886/`（DUT + Ref）  
**日志来源**：Jira X6886OS16-290 / FRBox 分享包

---

## 【结论先行】

- **问题定性**：DNS/网络验证类 + **系统 Trusted Credentials 被禁用**。WiFi 已关联+DHCP 成功后呈 `PARTIAL_CONNECTIVITY`（Limited connection）；空口/认证非主因。
- **根本原因**：系统受信任证书（Trusted Credentials）处于 disabled，导致公网 CA 链无法锚定。HTTPS 握手失败（`certificate_unknown` / `Trust anchor for certification path not found`），连通性探测不能 `IS_VALIDATED`，UI 显示 Limited connection。
- **验证结论（2026-10-03）**：按下列路径重新 **enable** 后问题消失，根因坐实为证书信任开关，**非 WiFi 驱动/射频**。
- **关键证据**：
  1. tcpdump：39 条失败 TLS Alert（35×`certificate_unknown`，2×`access_denied`）；`dialog-api.transsion-os.com` 叶子证 `*.transsion-os.com` / GeoTrust，**未过期**仍被客户端拒绝。
  2. main_log：大量 `SSLHandshakeException: Trust anchor for certification path not found`；SoftAP 窗 `Probe not validated` + `+PARTIAL_CONNECTIVITY`。
- **日志无法证明是用户当场手动关闭**：本次 APLog 窗口内无 Trusted Credentials 页面/KeyChain 禁用记录；该状态可在更早操作后持久生效。未看到 MDM 设备所有者。
- **影响范围**：HTTPS 与网络验证失败，WiFi 显示有限连接。
- **处理**：Settings → Password & Security → System Security → Encryption & Credentials → Trusted Credentials，将 disabled 项全部 enable。

> 详细推导见下方各章节。

---

## 【日志完整性】

- [x] main log: `logs/extracted/Wifi -x6886/DUT/.../main_log_2__2026_0930_132122`（另有 Ref main_log）
- [x] kernel log: `.../kernel_log_7__2026_0930_132122`（已转 `.localtime`）
- [x] tcpdump: `.../tcpdump_NTLog_V2_2026_0930_131918_start_1.cap`（DUT/Ref 均有）
- [x] 空口 log: `connsys_picus_log_*`（已提供；本问题主因在网络验证/上游，未作为主证据链）

**分析局限性**：无独立 802.11 sniffer。对照机晚约 7 分钟连同一 SoftAP 且验证通过，现已由 Trusted Credentials 复测闭环，不再把 SoftAP 上游不稳作为主因。本次 log **不能还原证书是何时、被谁 disable 的**。

---

## 【项目匹配】

- **匹配项目**：X6886-tOS16 / WIFI-Performance / Pakistan Overseas
- **匹配案例**：
  - **CASE-029**（证书相关）：`PROBE_HTTPS` + `SSLPeerUnverifiedException` / 证书 mismatch（本案为信任锚缺失 + `certificate_unknown`，机制同类）
  - **CASE-019**（现象相关）：Probe 失败 → 无互联网/感叹号，`EVER_EVALUATED` 无 `IS_VALIDATED`
- **分析依据**：TLS Alert 全量统计见 `tls_alert_inventory.txt`；TAG：网络验证失败 / PARTIAL / 证书信任 / Trust anchor

---

## 【总体统计】

| 指标 | 数值 |
|------|------|
| DUT 连接尝试 | 1 次（`Infinix GT 50 Pro`） |
| L2/认证/DHCP 成功 | 1 |
| NetworkMonitor VALIDATED | 0 |
| PARTIAL / Limited connection | 1 |
| Ref 同 AP 连接 | 1（约 13:27，`+VALIDATED`，Probe `response=204`） |

---

## 【每次尝试详细分析】

### DUT 会话（net 114 / wlan0）

| 时间 | 阶段 | 结果 |
|------|------|------|
| 13:19:55.971 | `WifiService: connect` package=`com.android.systemui` | SystemUI 发起（非 Settings 手动包名，但用户在 WiFi 页操作后由框架连接） |
| 13:19:56.017 | Associate SSID `Infinix GT 50 Pro` | 成功 |
| 13:19:56.143 | 4-way + `CTRL-EVENT-CONNECTED` BSSID `62:79:a4:85:01:cd` | 成功 |
| 13:19:56.249 | `networkAddInterface(114, wlan0)` | WiFi 传输侧确认 |
| 13:19:56.3xx | DHCP → IP `10.224.249.190`，GW/DNS `10.224.249.195` | 成功 |
| 13:19:56.567 | UI `No internet` | 尚未验证 |
| 13:20:04 | score `+EVER_EVALUATED`（无 `+IS_VALIDATED`） | 探测结束但未通网 |
| 13:20:06~26 | `Probe result: not validated`；Ping 4~13ms 成功 | 半通 |
| 13:20:14 | `+PARTIAL_CONNECTIVITY` → UI **Limited connection** | 失败定性 |
| 13:20:26.598 | `setWifiEnabled ... enable=false`（SystemUI） | **用户关闭 WiFi** |
| 13:20:26.627 | `CTRL-EVENT-DISCONNECTED reason=3 locally_generated=1` | 关 WiFi 导致本地断开 |

### Ref 会话（net 104 / wlan0，约 13:27）

| 时间 | 阶段 | 结果 |
|------|------|------|
| 13:27:41 | 同 SSID/同 BSSID 连接，IP `10.224.249.62` | 成功 |
| 13:27:41.955 | `+VALIDATED` / `+EVER_VALIDATED+IS_VALIDATED` | 通网 |
| 13:27:51 | `Probe result: {success=true, time=534ms, response=204}` | OEM Probe 成功 |

---

## 【失败原因分类】

| 模式 | 次数 | 特征 |
|------|------|------|
| PARTIAL_CONNECTIVITY / Limited connection | 1 | Ping 网关成功 + HTTPS/Probe 失败 → UI Limited |
| 系统 CA 信任失败 | 整机 | `certificate_unknown` + Trust anchor missing；enable Trusted Credentials 后恢复 |
| 用户关 WiFi | 1 | `setWifiEnabled(false)`，非 AP 踢线 |

**排除项**：
- 非弱信号（RSSI 约 -42~-35 dBm）
- 非认证/4-way 失败
- 非 DHCP 失败
- 非网关 ARP/NUD 失败（Ping 成功、网关可达）

---

## 【关键日志】

### DUT — 半通与 Limited connection

```
13:19:56.143  CTRL-EVENT-CONNECTED ... 62:79:a4:85:01:cd  (SSID Infinix GT 50 Pro)
13:19:56.249  networkAddInterface(114, wlan0)
13:20:06.462  WifiNetworkCheck: Probe result: not validated
13:20:06.478  WifiNetworkCheck: Ping result: {success=true, time=13ms}
13:20:14.163  Update capabilities for net 114 : +PARTIAL_CONNECTIVITY
13:20:14.169  Tile.TrWifiTile: secondaryLabel=Limited connection
13:20:12/25   SocketTimeoutException: graph.facebook.com:443 from 10.224.249.190
13:20:26.598  WifiService: setWifiEnabled ... enable=false
13:20:26.627  CTRL-EVENT-DISCONNECTED reason=3 locally_generated=1
```

### DUT tcpdump — HTTP 探测曾返回 204，但 HTTPS/部分公网不稳

- `GET connectivitycheck.gstatic.com/generate_204` → `HTTP/1.1 204`（至少 2 次）
- DUT 额外解析 `connectivitycheck.gstatic.cn`；Ref 主要只走 `gstatic.com`
- 对 `ota-checker.transsion-os.com` 等目的：ClientHello 重传、无完整业务；应用层多 `Failed to connect ...:443`

### Ref — 同 AP 验证通过

```
13:27:41.955  Update capabilities ... +VALIDATED
13:27:41.955  Update score ... +EVER_VALIDATED+IS_VALIDATED
13:27:51.998  Probe result: {success=true, time=534ms, response=204}
```

---

## 【问题原因】

### 根本原因（综合）

1. **系统 Trusted Credentials 被禁用（已复测确认）**：公网 CA 签发证书仍被客户端 `certificate_unknown` 拒绝，main_log `Trust anchor for certification path not found`。测试将 Trusted Credentials 中 disabled 项全部 enable 后问题消失。  
2. **网络验证失败（PARTIAL）**：SoftAP net 114 / `10.224.249.190` Ping 网关成功，`WifiNetworkCheck` Probe 未验证 → `+PARTIAL_CONNECTIVITY` → Limited connection。HTTP `generate_204` 可 204，HTTPS 探测不完整。  
3. **Alert 出现位置**：明文 `certificate_unknown` 主要在蜂窝 IP `10.209.98.181`；SoftAP 会话窗内少见同款明文 Alert，但整机信任库异常可同时毁掉 HTTPS 探测。  
4. **无法从本次 log 判定“用户当场手动关闭”**：无 `TrustedCredentials` Activity、无 KeyChain 禁用 API、无 `cacerts-removed` 写入痕迹。窗口内设置页是关于手机/系统更新/工程师模式/抓 log/Wi-Fi。Chrome `deviceOwned:false`，不像 MDM。禁用是持久状态，动作可发生在本次 APLog 之前。  
5. **断开原因**：SystemUI `setWifiEnabled(false)`，非 AP 踢线。

### 空口/驱动侧

- RSSI 强（约 -42 dBm），PER 低，**非射频/关联问题**。

---

## 【流程总结】

**成功路径（Ref）**  
Assoc → 4-way → DHCP → Probe 204 → `+VALIDATED` → 可上网

**失败路径（DUT）**  
Assoc → 4-way → DHCP → Ping OK → Probe not validated → `+PARTIAL_CONNECTIVITY` → UI Limited connection → 用户关 WiFi

---

## 【链路质量曲线图】

### 链路质量四象限图（含连接状态）
![链路质量曲线](X6886OS16-290_link_quality.png)

### Kernel Metrics
![Kernel Metrics](X6886OS16-290_kernel_metrics.png)

---

## 【连接状态时间轴】

![连接状态时间轴](X6886OS16-290_timeline.png)

---

## 【建议措施】

1. **已验证有效**：Settings → Password & Security → System Security → Encryption & Credentials → Trusted Credentials，将 disabled 项全部 enable。  
2. 同类单优先查 tcpdump TLS Alert（`certificate_unknown` / `access_denied`）和 main_log `Trust anchor for certification path not found`，不要先当 WiFi 驱动问题。  
3. 若需证明“谁关的开关”：必须抓到操作当时的 Settings/KeyChain log，或检查机内 `cacerts-removed`；**仅凭问题现场 APLog 不够**。  
4. 出厂默认系统 CA 为启用；OTA 一般不会批量 disable。排除 MDM 后，更常见是更早的人工/售后设置残留。

---

## 【TAG】

`网络验证失败` `部分连通PARTIAL_CONNECTIVITY` `无互联网` `证书信任` `Trust anchor` `certificate_unknown` `access_denied` `SSLHandshakeException` `Trusted Credentials` `Ping成功Probe失败` `SoftAP`

---

## 【案例素材】

已入库 **CASE-039**（`auth-failure/CASE-039_X6886OS16-290_TrustedCredentials禁用导致Limited connection.md`）。

---

## 【飞书推送】

本地报告已生成。当前仓库未找到可用的 `scripts/feishu_import_docx.py`，飞书推送暂未执行；可稍后补推。
