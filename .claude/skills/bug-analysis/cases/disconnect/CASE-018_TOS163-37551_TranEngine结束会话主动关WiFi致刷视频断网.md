# CASE-018: TranEngine 结束会话主动关 WiFi 致刷视频断网

## 基本信息
- **案例ID**: CASE-018
- **分类**: disconnect
- **来源**: TOS163-37551
- **创建时间**: 2026-06-18
- **匹配次数**: 0

## 现象描述
- 中国粉丝反馈：WiFi 使用中**开关自动关闭**，用户未手动操作；正**刷微信视频**时发现 WiFi 已关
- 机型 CN6（TECNO XYZ），HiOS 16.3.0 / Android 16，MTK 平台
- 偶现（once）；问题时间 2026-06-18 **07:00:51**（Asia/Shanghai）
- SSID **Kdevil006**（WPA_PSK，BSSID 80:ea:07:f7:e5:d3）
- 反馈来源：**TranEngine**

## 根因结论
**非 WiFi 驱动/连接故障。`com.transsion.tranengine` 在会话结束（`isTranEngineEnabled: false`）时调用 `setWifiEnabled(false)` 主动关闭 WiFi 开关，导致 `CTRL-EVENT-DISCONNECTED reason=3 locally_generated=1`。用户刷微信视频时屏幕已熄灭约 8s，TranEngine 关 WiFi 后视频断网。**

机理链条：
1. **04:48:52** TranEngine 曾 **`setWifiEnabled(true)`** — 诊断/反馈流程会接管 WiFi 开关
2. **06:57** 前台 **com.tencent.mm** 播放视频，`WIFI_STREAM_ON: true`，WiFi 连接正常
3. **06:57:52** 屏幕熄灭（`SCREEN_OFF`），微信仍为前台
4. **06:58:00.868** TranEngine → **`setWifiEnabled(false)`**，伴随 `isTranEngineEnabled: false`
5. **06:58:00.921** wpa_supplicant 本机主动断开（`locally_generated=1`），非 AP 踢出
6. **07:00:26** 用户从 **SystemUI** 手动重新打开 WiFi
7. **07:00:51** 用户通过 TranEngine 提交反馈并抓 TagLog

## 排查步骤
1. main_log 搜 **`setWifiEnabled`**，确认 `package=` 与 `enable=` 值
2. 区分 **`locally_generated=1`**（本机关 WiFi）vs AP 踢出（reason 其他）
3. 对齐 **TranEngine / TagLog / CaptureLog** 时序（`CreateTaglogService`、`isTranEngineEnabled`）
4. 查前台是否视频/流媒体（`VideoSceneManager`、`WIFI_STREAM_ON`）
5. 排除 WiFi 驱动崩溃、link loss、用户手动关 WiFi（`settings.wifi` / SystemUI toggle 时序）
6. 查 TranEngine 是否曾 **`setWifiEnabled(true)`**（背景 log 包）

## 关键日志
```
// TranEngine 曾主动开 WiFi
06-18 04:48:52.829  WifiService: setWifiEnabled package=com.transsion.tranengine enable=true

// 刷视频，WiFi 流媒体正常
06-18 06:57:01.446  BleScanAndAdvertisePolicy: WIFI_STATE: 1, WIFI_STREAM_ON: true
06-18 06:57:03.084  VideoSceneManager: handlerVideoStart ... pkgName = com.tencent.mm

// 熄屏后 TranEngine 关 WiFi
06-18 06:57:52.659  DreamAnimation: from normal to screenoff
06-18 06:58:00.868  AiNetControllerService: isTranEngineEnabled: false, mIsTranEngineEnabled: true
06-18 06:58:00.868  WifiService: setWifiEnabled package=com.transsion.tranengine enable=false
06-18 06:58:00.921  wpa_supplicant: CTRL-EVENT-DISCONNECTED ... reason=3 locally_generated=1
06-18 06:58:00.997  TranWifiSmartAssistantController: Turn off the screen for more than 6s, default user not present

// 用户手动恢复
06-18 07:00:26.772  WifiService: setWifiEnabled package=com.android.systemui enable=true
06-18 07:00:29.139  wpa_supplicant: CTRL-EVENT-CONNECTED ... Kdevil006
06-18 07:00:51.156  DebugLoggerUI/CreateTaglogService: onStartCommand
```

## TAG
- TranEngine 副作用
- WiFi 开关异常
- setWifiEnabled
- locally_generated
- 非WiFi驱动故障
- 刷视频断网
- com.tencent.mm
- WIFI_STREAM_ON
- SCREEN_OFF
- CaptureLog
- TagLog
- CN6
- MTK平台
- 中国

## 匹配条件
- 用户描述「WiFi 自己关了 / 开关变关闭」且未手动操作
- log 中存在 **`setWifiEnabled package=com.transsion.tranengine enable=false`**
- disconnect 为 **`reason=3 locally_generated=1`**
- 反馈来源为 **TranEngine** 或伴随 TagLog/CaptureLog 流程
- 非 link loss、非 AP 踢出、非 tear down wlan0

## 建议措施
1. **转 TranEngine 团队**：排查 `setWifiEnabled(false)` 调用链；不应在使用网络（尤其视频/流媒体）时关 WiFi，或应恢复用户原 WiFi 开关状态
2. **WiFi 团队**：可关单/打回 — 日志证明为应用层主动关闭
3. **复现**：TranEngine 反馈流程结束 + screen off + 视频后台播放场景挂测

## 相关案例
- CASE-012：Shopee 应用层误报 + WifiNetworkQuality tear down wlan0（同为「感知断网」但根因不同）
- CASE-014：驱动层误漫游 WRONG_KEY 断网（本案例无漫游、无 WRONG_KEY）
