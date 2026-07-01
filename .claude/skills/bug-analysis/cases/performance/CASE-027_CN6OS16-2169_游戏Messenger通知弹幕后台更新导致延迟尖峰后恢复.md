# CASE-027: 游戏时 Messenger 通知弹幕 + 后台更新导致 WiFi 延迟尖峰后恢复（WiFi 未断开）

## 基本信息
- **案例ID**: CASE-027
- **分类**: performance
- **来源**: CN6OS16-2169
- **创建时间**: 2026-06-30
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝玩 Mobile Legends 时，**Messenger 通知弹出后 WiFi 连接变慢，约 20s 后逐渐恢复**
- 机型 TECNO CN6（XYZ），CN6-16.3.0.132SP01 FANS，hios16.3.0 / Android 16，MTK 平台
- 高概率；问题时间 2026-06-27 23:28:25（Asia/Manila）
- 截图：游戏内 Ping **125ms（红色）**，WiFi 图标**满格**
- 关键：WiFi **未断开**，`Wifi network validated`；粉丝描述「变慢后恢复」与日志一致

## 根因结论
**游戏前台 + Messenger 聊天通知触发 GameMode 弹幕弹窗 + Play Store 对 Messenger 静默 SplitInstall 更新，与游戏流量争用 CPU/带宽，导致空口 PER 间歇升至 50~85、网关 Ping 延迟尖峰至 82~103ms、游戏 RTT 125ms；后台任务结束后延迟自动恢复。非 RSSI 弱信号或 WiFi 断连。**

机理链条：
1. **23:27:44** `onNotification: pkg=com.facebook.orca` → `ShowBarrageHelper: showBarrageWindow` → **GameMode Barrage Heads Up**
2. **23:28:12~21** Play Store `IQ: proceed install com.facebook.orca`，PACKAGE_REMOVED/replacing（静默更新与游戏并发）
3. 网关 Ping：4~14ms → **82ms（23:28:24）** → **103ms（23:28:34）** → **14ms（23:28:44）** 恢复
4. Kernel `wlanLinkQualityMonitor`：PER **50~85**，Tx 速率降至 **585~1755**（争用特征，类 CASE-008）
5. SKIN **MODERATE ~50°C**，CPU 负载 **79~99%**（KunPeng `cpu_h_loading`）
6. 全程无 disconnect/deauth

## 排查步骤
1. 框架层对齐 `onNotification` / `showBarrageWindow` 时间与粉丝问题时刻
2. 查 `WifiStatistics:WifiNetworkCheck: Ping result` 时间线是否「尖峰 → 恢复」
3. 查 Play Store / `Finsky:background` 是否同期安装/更新通知来源 App
4. kernel `wlanLinkQualityMonitor` 看 PER 突刺、Tx 速率是否下降
5. 确认无 disconnect；对比游戏内 RTT 与网关 Ping

## 关键日志
```
// 通知 → 弹幕（main_log）
23:27:44  TranAuraController: onNotification: pkg=com.facebook.orca, channel=Chats
23:27:44  ShowBarrageHelper: showBarrageWindow com.facebook.orca
23:27:48  BufferQueueProducer: [GameMode Barrage Heads Up] max=288.95ms

// Ping 变慢 → 恢复
23:27:44  Ping result: {success=true, time=4ms}
23:28:24  Ping result: {success=true, time=82ms}
23:28:34  Ping result: {success=true, time=103ms}
23:28:44  Ping result: {success=true, time=14ms}

// 后台更新
23:28:12  Finsky:background: IQ: proceed install [Package:com.facebook.orca]
23:28:20  onPackageRemoved com.facebook.orca, replacing=true

// kernel
wlanLinkQualityMonitor: Tx(rate:1755,...), PER(56)
wlanLinkQualityMonitor: Tx(rate:585,...),  PER(85)
```

## TAG
- 游戏延迟尖峰
- Messenger通知
- GameMode弹幕
- showBarrageWindow
- 后台更新争用
- SplitInstall
- PER间歇突刺
- 网关Ping尖峰
- 无断开
- WiFi未断开
- 强信号满格
- 游戏卡顿
- Mobile Legends
- CN6
- 菲律宾
- 粉丝反馈
- MTK driver

## 建议措施
1. GameMode/SmartPanel：游戏前台限制 IM 类 App 弹幕弹窗，抑制 Play Store 静默更新
2. 粉丝侧：关闭 Messenger 游戏弹幕或开启游戏勿扰；Play Store 改为非游戏时段更新
3. 评估游戏场景 WMM/游戏加速对 UDP 游戏流保障是否不足
4. 与 CN6OS16-2216（同机后续反馈）合并跟踪

## 数据局限
- 有 main_log + kernel_log + connsys_picus；tcpdump 未提供
- 游戏内 125ms RTT 为截图佐证，未在系统日志中直接打印

## 相关案例
- CASE-008（强信号 PER 突刺空口争用）
- CASE-028（同机 CN6OS16-2216，未见 Ping 尖峰，更偏温控/FPS）
