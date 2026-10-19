# CASE-046: 飞行模式+关 WiFi 期间“收到 WhatsApp 消息”为用户误判 — 消息于关飞行模式连 WiFi 后同步，显示发送方时间

## 基本信息
- **案例ID**: CASE-046
- **分类**: disconnect
- **来源**: TOS163-47124
- **创建时间**: 2026-10-19
- **匹配次数**: 0

## 现象描述
- 埃及粉丝反馈（feedbackId 382411233，Critical / occasional）：Something happened twice. I turned off my Wi-Fi and enabled Airplane Mode, then, couple of hours later, when I checked my phone, I found that I had received WhatsApp messages while Airplane Mode was on and Wi-Fi was off.
- 机型 TECNO LK7，Android 16 / hios16.3.0（LK7-16.3.0.142(OP002PF001AZ)FANS），MTK MT6631
- 家庭 WiFi **WE_1C12CC**（2.4G ch1，BSSID `04:8c:16:1c:12:d4`，RSSI 中位 -79 dBm）
- 用户时区 Africa/Cairo（UTC+3）；kernel `.localtime` 为 UTC，需 +3h 与 main log 对齐

## 根因结论

**非 WiFi / 飞行模式缺陷。飞行模式 2h44m 期间设备无任何数据通道，WhatsApp 未收到任何消息；消息是在用户关闭飞行模式、打开 WiFi 并连上 WE_1C12CC 后才同步下来的。WhatsApp 显示发送方时间（落在飞行期间），导致用户误以为“飞行模式下收到消息”。**

机理链条：
1. **05:41:54** 用户控制中心关 WiFi（`setWifiEnabled package=com.android.systemui enable=false`）→ `CTRL-EVENT-DISCONNECTED reason=3 locally_generated=1` → `no longer has a default network`
2. **05:41:55** `TrAirplaneModeTile: click airplane` → 飞行模式 ON，`Turning radio off - airplane`
3. **05:42:03** 用户点开 WhatsApp，`badge_num=98`
4. **05:57 ~ 08:00** WhatsApp 后台重连 `g.whatsapp.net` 全部 `Network is unreachable` / `UnknownHostException`；08:00 ~ 08:26 kernel `driver is not ready`
5. **08:26:04** 飞行模式下用户先点 WiFi 开关 → **08:26:05** 关飞行模式
6. **08:26:14** 用户点开 WhatsApp，`badge_num=98`（与飞行前相同，飞行期间未读数无变化），仍 `Network is unreachable`
7. **08:26:27** 连上 WE_1C12CC，`networkAddInterface(177, wlan0)`，`+VALIDATED`
8. **08:26:32** WhatsApp 首批 `Message notifications` ×3，角标 99 —— 消息在联网后到达

## 问题窗口统计

| 指标 | 数值 |
|------|------|
| 飞行模式时长 | 05:41:55.97 → 08:26:05.82，**2h44m10s** |
| 飞行期间默认网络 | **无**（05:41:54 → 08:26:27） |
| 飞行期间 WhatsApp 消息通知 | **0** |
| 飞行前后 WhatsApp 角标 | **98 → 98** |
| 恢复后首条消息通知 | 08:26:32.25（WiFi VALIDATED 后 4.4s） |
| 开 WiFi → 自动连上 | 约 22.5s（附带发现） |

## 附带发现（P3，与投诉无因果）
- 开 WiFi 后驱动扫描 #1（08:26:06.76）、#2（08:26:11.65）均已命中 WE_1C12CC，但框架未自动连接；约 20s 后扫描 #3（08:26:25.79 → 27.26）完成后立即关联成功（assoc 全程 71ms）
- 08:26:27.04 框架 `ScanResultUtil: Empty or null ScanResult list`
- 推测：连接时 `cRSSI[-80]` / `rssi=-82` 处于 2.4G 入网门限边缘，或扫描 #1 结果在退出飞行模式 + 国家码重设（08:26:07.58）时被丢弃；user 版本无选网日志，未坐实
- 重连后链路：重传率 18.3%、失败率 31.3%、ACK fail 占比 91.7%、Rx 错误率 15.9% → 场景 D（上行链路失效型，弱信号所致）

## 排查步骤

1. **定位用户操作窗口**：`Tile.TrAirplaneModeTile: click airplane` + `WifiService: setWifiEnabled`，还原开/关飞行模式与 WiFi 的先后顺序
2. **确认窗口内是否有数据网络**：`default network` / `ConnectivityService: Update score for net` / `netd: networkAddInterface(<id>, <ifName>)` 定传输侧；注意 ccmni 网络可能是 IMS（移动数据关闭 `onDataEnabledChanged: enable: false` 时非默认网）
3. **确认 App 侧确实不可达**：WhatsApp `msys` 的 `Network is unreachable` / `UnknownHostException`
4. **对比角标**：`LauncherPreAnalytics ... launcher_icon_click ... pkg=com.whatsapp ... badge_num=` 与 `tBadge ... unreadNum`，比较飞行前后未读数
5. **定位消息到达时间**：`TranAuraController: onNotification: pkg=com.whatsapp ... Message notifications`，与 `+VALIDATED` 时间比较
6. **排除误归属**：`msgr.msys ... connection/new_state` 属于 Facebook Messenger（com.facebook.orca），非 WhatsApp
7. **kernel 时区**：MTK `.localtime` 内嵌 `UTC;android time` 锚点时为 UTC，需按 timezone 加偏移

## 关键日志

```
// 关 WiFi + 开飞行模式
08-09 05:41:54.122  WifiService: setWifiEnabled package=com.android.systemui uid=10144 enable=false
08-09 05:41:54.166  wpa_supplicant: wlan0: CTRL-EVENT-DISCONNECTED bssid=04:8c:16:1c:12:d4 reason=3 locally_generated=1
08-09 05:41:54.364  NetworkUtil: The application no longer has a default network. The last default network was 174
08-09 05:41:55.969  Tile.TrAirplaneModeTile: click airplane, current mState.value=false
08-09 05:42:03.333  LauncherPreAnalytics: launcher_icon_click ... pkg=com.whatsapp ... badge_num=98

// 飞行期间 WhatsApp 不可达
08-09 05:57:35.664  msys: ... UnknownHostException: Unable to resolve host "dit.whatsapp.net"
08-09 05:57:35.886  msys: ... (endpoint=g.whatsapp.net:443) -> Network is unreachable

// 开 WiFi + 关飞行模式 + 消息到达
08-09 08:26:04.929  Tile.TrWifiTile: click wifi, current mState.value=false
08-09 08:26:05.824  Tile.TrAirplaneModeTile: click airplane, current mState.value=true
08-09 08:26:14.804  LauncherPreAnalytics: launcher_icon_click ... pkg=com.whatsapp ... badge_num=98
08-09 08:26:27.397  wpa_supplicant: wlan0: CTRL-EVENT-CONNECTED - Connection to 04:8c:16:1c:12:d4 completed
08-09 08:26:27.474  netd: networkAddInterface(177, wlan0)
08-09 08:26:27.901  ConnectivityService: Update capabilities for net 177 : +VALIDATED
08-09 08:26:32.255  TranAuraController: onNotification: pkg=com.whatsapp ... mName=Message notifications
08-09 08:26:32.889  tBadge_transsionapp-RECEIVE-: unreadNum is 99 ... com.whatsapp/com.whatsapp.Main
```

## TAG
- 飞行模式
- TrAirplaneModeTile
- setWifiEnabled
- SystemUI快捷开关
- 无默认网络
- Network is unreachable
- UnknownHostException
- networkAddInterface定传输侧
- WhatsApp
- badge_num
- 离线消息同步
- 发送时间戳误解
- 非WiFi问题
- 用户误判
- 自动重连慢
- RSSI低
- 2.4G频段
- 粉丝反馈
- LK7
- 埃及
- MTK平台

## 建议措施

### 用户回复
1. 按“非 bug / 预期行为”回复：飞行模式期间手机完全断网未收到消息；消息于关闭飞行模式、WiFi 连上后同步，WhatsApp 显示的是发送方时间
2. 追问另一次发生前是否在飞行模式下手动开过 WiFi/蓝牙（Android 14+ 会记住该选择，之后开飞行模式 WiFi 保持开启）；如复现请抓取开飞行模式时刻日志及 `settings get secure wifi_apm_state`

### 附带体验点（可选）
3. 内部用 verbose WiFi 日志复现“退出飞行模式同时开 WiFi + 目标 AP 约 -80 dBm”，确认首轮扫描是否被入网门限过滤或在国家码重设时被丢弃

## 关联案例
- **CASE-022**（部分相似）：WhatsApp 现象，WiFi 链路正常，应用层行为
- **CASE-025 / CASE-028**（部分相似）：用户主观误判，WiFi 实际正常
- **CASE-023**（弱相关）：框架未及时自动重连已保存网络（本案扫描已命中，CASE-023 为扫描未命中）

## 分析报告
- `AI-result/issues/TOS163-47124/TOS163-47124-analysis.md`
- 本地日志：`AI-result/issues/TOS163-47124/logs/`
