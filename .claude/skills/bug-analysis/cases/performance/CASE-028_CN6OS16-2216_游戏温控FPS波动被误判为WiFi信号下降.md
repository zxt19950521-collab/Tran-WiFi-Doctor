# CASE-028: 游戏温控 FPS 波动被误判为 WiFi 信号下降（WiFi 链路正常）

## 基本信息
- **案例ID**: CASE-028
- **分类**: performance
- **来源**: CN6OS16-2216
- **创建时间**: 2026-06-30
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝（**与 CASE-027 同机** SN 171622565E000046）玩 Mobile Legends 时，**通知弹出后感觉 WiFi 信号下降并卡顿**
- 机型 TECNO CN6，CN6-16.3.0.132SP01 FANS，hios16.3.0 / Android 16
- 标称必现；粉丝标注问题时间 2026-06-30 11:07:57（实为提交反馈时刻）
- 关键：日志显示 WiFi **RSSI 强（-34~-45 dBm）**、Ping **4~14ms 全成功**、无断连；未见 TranWifi 弱网弹窗或信号下降系统通知

## 根因结论
**非 WiFi 射频故障。游戏长时运行 SKIN 升至 MODERATE（~47°C）导致 FPS/帧时延尖峰（max frame 383ms），用户将卡顿与「WiFi 信号下降」主观关联；本案日志未见 Messenger 弹幕与网关 Ping 尖峰（对比 CASE-027 同机更早反馈）。**

机理链条：
1. 游戏约 26min（10:41~11:07），网关 Ping 全程 4~14ms，`current rssi is sufficient`
2. SKIN **MODERATE ~47°C**，FPS 从 90 降至 61~78；**11:04:34** max frame **383ms**
3. KunPeng `game_exp`：19min 窗口 jank=2，WiFi 归因 jank=2
4. Kernel PER 多数 0~5，偶发 50 尖刺未引起 Ping 失败
5. 11:07:29 用户手势切出游戏；11:07:57 为 xFeedback 提交，非卡顿峰值
6. 游戏模式 `isHeadsUpPinned` 始终 false，未抓到通知置顶日志

## 排查步骤
1. main_log 查 RSSI/Ping/validated，排除断连与 Probe 失败
2. 查游戏 FPS/温控（SKIN MODERATE、PowerHAL fps 限制）
3. kernel `wlanLinkQualityMonitor` 查 PER/速率，区分 RF 问题 vs 系统侧卡顿
4. 确认问题时刻是否为反馈提交时间而非游戏卡顿峰值
5. 若粉丝坚持信号图标下降，要求录屏区分状态栏图标 vs 系统弹窗

## 关键日志
```
// WiFi 正常
11:00~11:07  Ping result: {success=true, time=4~8ms}
11:07:52     ====>>rssi :-41  /  current rssi is sufficient
11:07:52     Wifi network validated（同期）

// 卡顿（渲染/温控）
11:04:34  BufferQueueProducer: [MobaGameUnityActivity] fps=63.07 max=383.73ms
11:04:30  SKIN CurrentValue: 47.289 ThrottlingStatus: MODERATE
11:05:03  PowerHalWrapper: fps=60（约12s后恢复90）

// KunPeng
game_exp: _fps_avg=87.84, _jank_num=2, _jank_num_in_wifi=2
```

## TAG
- 游戏卡顿
- 非WiFi断连
- 强信号
- 温控MODERATE
- FPS波动
- 帧时延尖峰
- 用户误判
- 粉丝体验类
- Mobile Legends
- GameMode
- CN6
- 菲律宾
- 粉丝反馈

## 建议措施
1. 复现时录屏，明确是状态栏 WiFi 图标变化还是系统弹窗
2. 性能/温控组排查 MODERATE 档位游戏 FPS 限制策略
3. 与 CASE-027 合并：同机重复投诉，2169 有 Ping 尖峰+Messenger 弹幕，2216 更偏系统侧
4. 当前日志不足以支撑 WiFi 缺陷结论

## 数据局限
- 未发现 WiFi 信号下降通知日志；kernel 无 `.localtime` 墙钟对齐
- 问题标注时间与实际卡顿峰值（11:03~11:04）存在偏差

## 相关案例
- CASE-027（同机 CN6OS16-2169，Messenger 通知+Ping 尖峰，证据更完整）
- CASE-006（弱信号 PER 高致游戏卡顿，本案 RSSI 强、PER 低）
- CASE-008（空口拥塞 PER 突刺，本案 Rx error 极低）
