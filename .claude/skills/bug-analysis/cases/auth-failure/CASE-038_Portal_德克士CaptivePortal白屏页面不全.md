# CASE-038: 德克士 Dicos-WiFi Captive Portal 白屏 / 加载慢 / 页面不全（网关成段不回应 SYN）

## 基本信息
- **案例ID**: CASE-038
- **分类**: auth-failure
- **来源**: TOS170-28746（Portal 本地日志：09-18 `dekesi.zip`、1004、1005）
- **创建时间**: 2026-10-01（2026-10-09 按 1005 完整抓包结论修订）
- **匹配次数**: 0

## 现象描述
- 连接门店 **Dicos-WiFi**（开放网 + CMPS/wifidog 类 Captive Portal）后，登录页出现三类问题：
  - **白屏**：标题栏只有"登录Dicos-WiFi"、没有 URL，或停在 gstatic，进不了登录页
  - **加载慢**：地址栏已是 `121.41.53.206`，进度条长时间卡住（1005 实测 63 秒）
  - **页面不全**：页面出来但无样式（logo 图裂、按钮/复选框为原生样式）
- 机型 Infinix X6878（XOS / Android 16，高通 wcn6450）；单号反馈"竞品可以连上"，出厂设置后更明显
- 偶现，不同日子发生率差异大
- 测试中多次 `reason=3 locally_generated=1` 为用户在 Settings 手动断开重连，非系统踢网

## 根因结论

**门户网关 `172.16.0.1` 会成段地不回应它自己应答的服务的 TCP SYN（被劫持的 HTTP 80、网关本机 8080 静态资源）；经网关转发到外网门户服务器 `121.41.53.206` 的连接从不丢。WebView 的关键请求撞上不回应时段即失败。**

门户登录三步与失败对应：
1. WebView `GET http://connectivitycheck.gstatic.cn/generate_204`（211.95.34.139:80）→ **网关劫持自己回** Loading 页、JS 跳 121.41 → 该步 SYN 无应答 = **白屏**
2. `GET 121.41.53.206/cmps/admin.php/api/login/...`（HTML、jquery.js、bootstrap.js、大图）→ **网关转发** → 三组日志 0 丢失
3. 登录页引用 `http://172.16.0.1:8080/cmps/static/...`（bootstrap.min.css、login1.css、jquery-1.10.2、logo）→ **网关本机 8080** → SYN 持续无应答 = **加载慢 + 页面不全**（WebView 两轮各 ~31s 建连超时后用无 CSS 的 HTML 渲染）

判定网关侧（非手机侧）的依据：
- 失败/成功 SYN 报文完全一致（MSS/SACK/TS/WScale、TOS、TTL、窗口），无端口复用
- 同一毫秒级窗口内发往 121.41 的 SYN 14–20ms 即应答，只有网关自身服务无应答
- host driver：`tx failed = 0`（帧已被 AP 确认）、TX/RX dropped = 0；慢加载 54s 内 RX 计数仅 +2（回包未到达手机）；RSSI -51 dBm、72 Mbps
- MAC/IP 全程不变；DNS 正常
- 劫持步确为网关应答：回包延迟 3ms（同 8080；121.41 为 15–20ms）、回门户 HTML 而非 204

偶现与概率波动的原因：
- 丢包**按目的 IP 成段**出现：同 IP 上一条被丢 → 5s 内下一条被丢 80–100%；上一条有应答 → 0–35%
- 受影响 IP 每天不同（.130 gstatic.com：09-18 3.5% / 10-04 75% / 10-05 75%；.139 gstatic.cn：48% / 1.1% / 3.9%）
- 只有 WebView 实际使用的 IP（RedirectUrl，多为 .139）或 8080 落在不回应时段才可感知；丢在后台探测上用户无感
- 推测与店内连接负载有关（手机侧无法证实）

已排除 / 不支持：
- **弱信号**：同位置正常手机不复现；1005 在 -51 dBm 下同样复现（09-18 版"弱链路 + off-channel 扫描致 CSS 丢段"结论已推翻）
- **缓存 / 下载量**：成功与失败下载内容一致，失败时是根本连不上
- **按客户端建连限速**：去掉重传干扰后丢包率与此前 SYN 数（含 443）无正相关
- **HTTPS SYN 诱发**：443 全无应答为门户认证前的正常策略；收 443 越多的 IP 未丢得更多（10-04/10-05 .139 的 443 量是 .130 的 2 倍，80 几乎不丢）；需对照实验最终确认

未闭环：网关为何成段不回应（需网关侧抓包）；"竞品可以 / 清数据后更明显"在 .139 上 3.9% vs 1.1%，样本 9 对 3 且非同时段，未能区分手机差异与时段差异。

## 排查步骤

1. **录屏对齐**：标题栏无 URL → 第 ① 步失败；地址栏 121.41 卡住 / 无样式 → 第 ③ 步失败
2. **mainlog**：`CaptivePortalLoginActivity: onPageStarted/onPageFinished`；白屏 = 连上后只有 `onPageFinished`、无 `onPageStarted`；慢加载 = `onPageStarted: 121.41.53.206` 到 `onPageFinished` 间隔数十秒
3. **tcpdump（关键）**：逐连接看 SYN 是否有 SYN-ACK，分 121.41:80 / 172.16.0.1:8080 / 211.95.34.130:80 / 211.95.34.139:80；对比 SYN 报文字段是否一致
4. **host_driver**：`tx failed`、`TX/RX dropped`、`wlan_dp_display_txrx_stats` RX 计数，排除手机收发问题
5. **按目的 IP 统计**丢包率与成段性（上一条丢 → 下一条丢的条件概率）
6. **勿误判**：gstatic 443 全无应答是门户正常策略；Loading 空页是门户设计；`reason=3` 核对是否用户手动关 WiFi

## 关键日志

```
// 1005 慢加载 + 页面不全（09:11:28 连上）
09:11:31.13  onPageStarted: 121.41.53.206
09:11:30.98~31.38  121.41:80 login HTML / jquery.js / bootstrap.js / png 全部 200（握手 15–19ms）
09:11:31.180~31.209  SYN 172.16.0.1:8080 ×6 → 重传 +1/+3/+7/+15s，0 SYN-ACK
09:12:02.661~02.828  SYN 172.16.0.1:8080 ×3 → 0 SYN-ACK
09:12:34.20  onPageFinished（63s）→ 渲染无 CSS 页面
driver: tx failed adjust from 0 to 0；RX packets 4100(09:11:36) → 4102(09:12:30)

// 1005 白屏（09:13:00 连上，相对时间）
+0.76s  SYN .139:80 → SYN-ACK 3ms（NetworkMonitor 判 portal）
+2.43s  onPageFinished（无 onPageStarted）
+2.45s / +2.73s  WebView SYN .139:80 ×2 → 重传至 +9.86s 均无 SYN-ACK
+15.4s  .139:80 恢复应答

// 1004 目录 1（正常手机）同机制白屏
10:02:11.84 / 12.10  SYN .139:80 → 第 5 次重传 10:02:27.3 才 SYN-ACK（15.5s）

// 成功对照（1005 09:12:48 连上）
8080 ×6 握手 3–69ms，0.3s 内 12 个资源全部 200
```

## TAG
- CaptivePortal
- Dicos-WiFi
- CMPS
- wifidog
- 白屏
- 加载慢
- 页面不全
- bootstrap.min.css
- 172.16.0.1:8080
- 121.41.53.206
- generate_204
- gstatic.cn
- 211.95.34.139
- SYN无应答
- 网关劫持
- 成段丢包
- CaptivePortalLogin
- NetworkMonitor
- X6878
- QCOM平台

## 建议措施

### 网关 / 门户侧（根因）
1. 复现时在网关 LAN 口同步抓包（`tcpdump -i <LAN口> host <手机IP>`），确认 SYN 是否到达、是否发出 SYN-ACK
2. 排查劫持模块（gw_port=8060）按目的地址维护的状态（连接跟踪 / NAT / 劫持规则）在不回应时段的变化，以及 8080 服务并发数、listen backlog、卡顿
3. 登录页 CSS/JS/图片与 HTML **同源托管**（迁到 121.41），禁止写死 `http://172.16.0.1:8080`，可直接消除页面不全

### 终端侧（体验优化，不解决根因）
1. CaptivePortalLogin 拉起后 N 秒（如 5s）仍无 `onPageStarted` 时自动 reload，或切换备用探测 URL（`.cn` ↔ `.com`）

### 复测 / 对照
1. X6878 与竞品机**同时、同 AP、同时抓包**：同时丢 → 网关整体问题；只 X6878 丢 → 查网关是否按客户端（MAC）区别对待
2. 关闭 HTTPS 探测复测：`adb shell settings put global captive_portal_use_https 0`（测完 `settings delete`），先确认 443 SYN 明显下降
3. Dicos-WiFi 改"使用设备 MAC"复测

## 关联案例
- **CASE-029**（中相关）：同为 Captive Portal / NetworkMonitor / gstatic 探测；CASE-029 为 bypass 后 VALIDATED 滞留不弹 Portal；本案为**认证页加载失败（网关不回应 SYN）**
- **CASE-019**（弱相关）：Probe / 感叹号体验；非本单主路径

## 分析报告
- `AI-result/issues/Portal/dekesi/1005/Portal-1005-analysis.md`（主报告，含 SYN 应答时间线）
- `AI-result/issues/Portal/dekesi/1004/Portal-1004-analysis.md`
- `AI-result/issues/Portal/Portal-analysis.md`（09-18 初版，弱链路结论已推翻）
