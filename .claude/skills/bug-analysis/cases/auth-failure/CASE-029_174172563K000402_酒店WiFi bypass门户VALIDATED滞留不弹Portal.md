# CASE-029: 酒店 WiFi bypass 门户后 VALIDATED 滞留 — NetworkMonitor 未复验不弹 Portal

## 基本信息
- **案例ID**: CASE-029
- **分类**: auth-failure
- **来源**: 174172563K000402（SN，无 Jira 单号）
- **创建时间**: 2026-06-08
- **匹配次数**: 0

## 现象描述
- 测试场景：连接 **IHG ONE REWARDS Free WI-FI**（linkbroad 酒店 Captive Portal）后无法上网
- 机型 TECNO CN6c，CN6c-16.3.0.115SP08(OP005PF001AZ)，MTK 平台
- 问题时间 **2026-06-27 20:08 ~ 20:10**（Asia/Shanghai）
- WiFi **已连接满格**（RSSI -50~-55 dBm），DHCP 正常，网关 Ping 2~16ms，**全程无 disconnect**
- 用户感知「WiFi 满格但上不了网」；问题窗内 **CaptivePortalLogin 未再次弹出**

## 根因结论

**非 WiFi 射频/驱动故障。用户在门户页点「直接使用此网络」后系统在网关仍劫持时标记 VALIDATED；AOSP NetworkMonitor 在 VALIDATED 后未再周期复验，不弹 CaptivePortalLogin；酒店网关 Portal 未真正完成或过期后继续 HTTP 劫持；第三方 App 无法解析 `location.replace` 门户 HTML。**

机理链条：
1. **20:00:13** 连接 IHG WiFi，DHCP `192.168.138.62/19`，`firstCaptivePortalDetected`
2. **20:00:52** 系统拉起 `CaptivePortalLoginActivity`
3. **20:01:01** `NetworkMonitor` `PROBE_HTTP generate_204` **ret=200**（门户 HTML）；HTTPS 证书 `CN=*.linkbroad.com`
4. **20:01:02** 用户点 **`menu_item_selected: 直接使用此网络`** → `wm_finish_activity` → `firstValidated`
5. **20:01~20:11** Network 152 Validation logs **末次框架 PROBE = 20:01:01**，无后续复验
6. **20:08~20:11** 厂商 `WifiStat:NetworkProbe` **每分钟 failed**，但不触发 `CaptivePortalLogin`
7. **20:09:05** 优酷等 App HTTP 200 返回 `portal.linkbroad.com/jump.php` + `location.replace`，按 JSON 解析失败
8. dump @20:11 仍 `IS_VALIDATED`，与 Probe 失败、HTTP 劫持矛盾

## 排查步骤

1. **排除射频**：RSSI、association、DHCP、网关 Ping 是否正常
2. **查门户生命周期**（`events_log`，非 main_log）：`CaptivePortalLoginActivity` 创建/销毁次数；是否出现 **「直接使用此网络」**
3. **查框架探测**（`dumpsys connectivity` Validation logs）：`PROBE_HTTP` 是否 ret=200 门户 HTML；末次 `PROBE_*` 时间
4. **区分两层 Probe**：
   - AOSP `NetworkMonitor` → 负责 validated / 弹 Portal
   - 厂商 `WifiStat:NetworkProbe` / `WifiNetworkCheck` → 仅统计，不弹 UI
5. **查 HTTP 劫持**：搜 `portal.linkbroad`、`jump.php`、`location.replace`
6. **查 App 侧**：`syntax error, pos 1, json : <html>` 表示 App 未按 Portal 处理
7. **查 validated 滞留**：`IS_VALIDATED` 与 Probe failed 并存

## 关键日志

```
// events_log：用户 bypass 门户
06-27 20:00:52  wm_create_activity: ...CaptivePortalLoginActivity...CAPTIVE_PORTAL
06-27 20:01:02  menu_item_selected: [0,直接使用此网络]
06-27 20:01:02  wm_finish_activity: ...CaptivePortalLoginActivity,finish-activity

// dump-networking Validation logs（Network 152）
2026-06-27T20:01:01  PROBE_HTTP http://connectivitycheck.gstatic.cn/generate_204 ret=200
  Content-Type: text/html  ← 门户 HTML，非 204
2026-06-27T20:01:01  PROBE_HTTPS ... SSLPeerUnverifiedException
  DN: CN=*.linkbroad.com
← 末次框架探测；20:02~20:11 无后续 PROBE

// 厂商 Probe（不弹 Portal）
06-27 20:08:05  WifiStat:NetworkProbe: Probe failed
06-27 20:09:05  WifiStat:NetworkProbe: Probe failed

// App 劫持无法自愈
06-27 20:09:05  httpBootNode: report response: ... 200 | <html>...location.replace("https://portal.linkbroad.com/jump.php?...
06-27 20:09:05  httpBootNode: report error: syntax error, pos 1, json : <html>...

// validated 滞留
NetworkAgentInfo{network{152} ... IS_VALIDATED ... firstValidated 365372296}
```

## TAG
- CaptivePortal
- 酒店WiFi
- IHG
- linkbroad
- NetworkMonitor
- VALIDATED状态滞留
- 直接使用此网络
- Probe失败
- CaptivePortalLogin
- portal.linkbroad.com
- location.replace
- 已连接无法上网
- 非WiFi射频故障
- 框架体验问题
- CN6c
- MTK平台

## 建议措施

### 用户 / 测试
1. **勿点「直接使用此网络」**；完成 linkbroad 门户认证流程
2. bypass 后：设置 → WiFi → **登录网络**，或浏览器访问触发认证
3. 避免一键清理杀掉 `captiveportallogin`

### 框架（优先，类 CASE-019）
1. `VALIDATED` 后 `NetworkMonitor` 复验失败（HTTP 非 204 / 门户劫持 / 证书 mismatch）时 **清除 VALIDATED** 并重新弹出 `CaptivePortalLoginActivity`
2. 用户点「直接使用此网络」时，若探测仍显示 Portal 劫持，**不应**标记 validated（或缩短复验周期）

### 厂商（可选）
3. `WifiNetworkCheck` Probe 持续失败时，可联动通知 ConnectivityService 触发框架复验

### WiFi 组
4. **无需射频/驱动修复**；环境类酒店门户 + 框架体验问题

## 关联案例
- **CASE-019**（高相关）：Probe 失败 + validated 状态不一致；本案为 **VALIDATED 后不复验、不弹 Portal**
- **CASE-012**（弱相关）：系统 WiFi 正常但用户感知断网（应用层）
- **CASE-021**（弱相关）：已连接 VALIDATED 但无法上网（VPN 路径，非 Portal）

## 分析报告
- `AI-result/issues/174172563K000402/174172563K000402-analysis.md`
