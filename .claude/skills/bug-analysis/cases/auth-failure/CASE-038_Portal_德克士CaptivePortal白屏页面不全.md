# CASE-038: 德克士 Dicos-WiFi Captive Portal 白屏 / 页面不全（CSS 丢段 + 探测 IP 黑洞）

## 基本信息
- **案例ID**: CASE-038
- **分类**: auth-failure
- **来源**: Portal（本地日志，无 Jira；`dekesi.zip`）
- **创建时间**: 2026-10-01
- **匹配次数**: 0

## 现象描述
- 测试场景：连接门店 **Dicos-WiFi**（开放网 + CMPS/wifidog Captive Portal）后认证页白屏或界面不全
- 机型 Infinix X6878，XOS 16.3.0 / Android 16，高通 wcn6450
- 问题时间 **2026-09-18 17:54 ~ 18:13**（Asia/Shanghai）
- L2 关联、DHCP（`172.16.0.198`）、网关可达正常；RSSI 约 **-71～-75 dBm**
- 三类观感：
  - **白屏 A**：地址栏已是 `121.41.53.206`，进度条卡住、正文白
  - **白屏 B**：地址栏停在 gstatic，进不了登录页
  - **页面不全**：有控件但样式/图片残缺
- 测试未完成浏览器认证 → 无 `IS_VALIDATED`（预期，不作为问题）
- 多次 `reason=3` 断连：用户白屏过久后 **Settings 手动关/开 WiFi 重试**，非系统因 `NO_INTERNET_PERMANENT` 自动踢网

## 根因结论

**门户登录页静态资源跨机拆分（云端 HTML + 局域网 8080 CSS）叠 2.4G 弱链路与全频段 off-channel 扫描，导致主 CSS TCP 丢段 → 白屏 A / 页面不全；另有路径因 RedirectUrl 锁到 `gstatic.cn`（211.95.34.139）后二次 :80 SYN 黑洞 → 白屏 B。未认证 443 SYN 风暴为加重因素。**

机理链条：
1. NetworkMonitor 并行探测 `gstatic.com`（.130）/ `gstatic.cn`（.139），**谁先判门户谁写入 RedirectUrl**；CaptivePortalLogin **只打开这一条**，失败不自动切换
2. 网关劫持 `generate_204` 返回 Loading HTML，JS 跳到 `http://121.41.53.206/.../login/`（正常设计）
3. 登录页 HTML 在 **121.41:80**，主 CSS `bootstrap.min.css`（~103KB）写死在 **`172.16.0.1:8080`**
4. **白屏 A / 不全**：CSS 传体时 host 日志有全频段扫描（含 5G，例 scanid 41191 / GMS NLP），`peer_rssi=-71`、`tx failed=38`；tcpdump 见 `lost_segment`、ACK 卡洞；成功对照 CSS **0.4s** 齐且无 TCP 异常
5. **白屏 B**：`.139:80` 首次 NM 探测成功，WebView 二次 SYN 无 ACK ~30s；流级 SYN-ACK 成功率 `.130` 约 **96.5%** vs `.139` 约 **51.7%**
6. 443：NetworkMonitor HTTPS + Athena（shalltry）+ GMS 等 SYN 黑洞重传抢空口；**非 CSS 直接路径**

## 排查步骤

1. **排除射频关联**：association / DHCP / 网关 Ping 是否正常
2. **分型看地址栏**：已是 `121.41` → A/不全；仍在 gstatic → B
3. **tcpdump**：
   - login HTML 是否 200
   - `172.16.0.1:8080` 上 `bootstrap.min.css` 是否在用户重试前 ~1s 内 200
   - CSS stream 是否有 `lost_segment` / dup ACK
   - `.139:80` vs `.130:80` SYN/SYN-ACK 比
4. **host_driver**：CSS GET 窗口 `scm_scan_event` 是否离台到 5G；`peer_rssi` / `tx failed` / MCS
5. **mainlog**：`isPortal=true` 的 RedirectUrl；`Forcing reevaluation` / `PROBE_HTTPS`；`setWifiEnabled` 是否来自 Settings
6. **勿误判**：Loading 空页是门户设计；`reason=3` 核对是否用户手动关 WiFi

## 关键日志

```
// 白屏 A：登录 HTML 到了，主 CSS 传体撞扫描
18:03:45.05   login HTML 200 @121.41.53.206
18:03:45.16   GET bootstrap.min.css -> 172.16.0.1:8080
18:03:45.xx   host: scm_scan_event freq 5180/5200/5220/5240 scanid 41191
18:03:45.xx   peer_rssi=-71 MCS2 19.5Mbps tx failed=38
18:03:45~46   tcpdump stream30: lost_segment, ACK stuck @68057
18:03:55      Settings setWifiEnabled false -> reason=3（用户重试）

// 成功对照
18:07:41.40   GET bootstrap.min.css
18:07:41.81   HTTP 200 content_length=102593（~0.41s，无 lost_segment）

// 白屏 B：锁 .cn 后二次建连黑洞
18:08:49.015  PROBE_HTTP gstatic.cn/.139 57ms 200 -> isPortal
18:08:49.030  PROBE_HTTP gstatic.com/.130 71ms（更晚，未采用）
18:08:49.348  onCreate for ...gstatic.cn/generate_204
18:08:49.612+ WebView SYN .139:80 -> 无 SYN-ACK ~30s
              无 onPageStarted 121.41 / 无 login GET

// 443 加重（摘录）
NetworkMonitor PROBE_HTTPS ... after 10000ms SocketTimeout
Athena --> retry upload https://ire-dsu.shalltry.com/...
```

## TAG
- CaptivePortal
- Dicos-WiFi
- CMPS
- wifidog
- 白屏
- 页面不全
- bootstrap.min.css
- 172.16.0.1:8080
- 121.41.53.206
- generate_204
- gstatic.cn
- 211.95.34.139
- SYN黑洞
- off-channel扫描
- GMS-NLP
- NetworkMonitor
- PROBE_HTTPS
- Athena
- shalltry
- 弱信号
- tx_failed
- lost_segment
- CaptivePortalLogin
- X6878
- QCOM平台

## 建议措施

### 门户侧（优先）
1. 登录页 CSS/JS/图片与 HTML **同源托管**，禁止写死 `http://172.16.0.1:8080`
2. 修复 `.139:80`（及同类）首次通、二次 SYN 黑洞；未认证 443 宜 RST 或放行探测域
3. 大图压缩；favicon 404（次要）

### 终端侧
1. 已 `CAPTIVE_PORTAL` 未 `VALIDATED`：**停/极低频 HTTPS 探测**；认证完成后再复检
2. 同上窗口：**推迟/禁止全频段 singleScan**（GMS NLP / Settings / system）
3. CaptivePortalLogin：探测 URL **短超时失败切换备用**（`.cn`→`.com`）
4. 门户期挂起 Athena 等非必要后台 HTTPS

### 复测
- 地址栏分型；CSS 是否 ~1s 内 200；CSS 窗是否仍有 5G off-channel；443 SYN 数量对比

## 关联案例
- **CASE-029**（中相关）：同为 Captive Portal / NetworkMonitor / gstatic 探测；CASE-029 为 bypass 后 VALIDATED 滞留不弹 Portal；本案为**认证页加载失败（CSS/探测 IP）**
- **CASE-019**（弱相关）：Probe / 感叹号体验；非本单主路径

## 分析报告
- `AI-result/issues/Portal/Portal-analysis.md`
