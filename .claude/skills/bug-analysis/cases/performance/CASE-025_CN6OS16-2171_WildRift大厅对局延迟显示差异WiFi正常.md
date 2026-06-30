# CASE-025: Wild Rift 大厅 41ms / 对局 5ms 与系统 WiFi 测试 3ms 不一致（WiFi 链路正常）

## 基本信息
- **案例ID**: CASE-025
- **分类**: performance
- **来源**: CN6OS16-2171
- **创建时间**: 2026-06-30
- **匹配次数**: 0

## 现象描述
- 菲律宾粉丝反馈：系统 **WiFi 网络测试约 3ms** 稳定；玩 **Wild Rift**（`com.riotgames.league.wildrift`）时首局界面显示 **45~50ms**，第二局降至约 **7ms**，怀疑 WiFi 不稳定
- 机型 TECNO XYZ (CN6)，Android 16 / HiOS 16.3.0（CN6-16.3.0.132SP01 FANS），**MTK** 平台
- WiFi SSID **Boss_atan5gzh**（5GHz 802.11ac，5180MHz），RSSI **-44~-53 dBm**；只出现一次
- 问题时间 2026-06-28 **16:46:11**（Asia/Manila）
- **用户截图佐证**（非日志）：
  - 大厅界面：`Network: 41ms`，`Network Type: Wi-Fi`
  - 对局内（03:56）：右上角延迟 **5ms**（绿色），FPS 61

## 根因结论

**WiFi 链路全程正常，不构成根因；用户将不同界面/不同探测对象的延迟数值混为一谈。**

机理链条：
1. **系统 WiFi 测试 3ms**：`WifiStatistics:WifiNetworkCheck` 的 **Ping** 结果为 **3~17ms**（均值 6.2ms），属**近端/网关级**探测；同模块 **Probe** 为 **68~263ms**、`response=204`（公网 HTTP 探测，参考 CASE-019 目标 `connectivitycheck.gstatic.com`）
2. **大厅 41ms**：游戏大厅 UI 显示到**游戏平台/登录匹配节点**的 RTT（用户截图 `Network: 41ms`），与系统 3ms **测量对象不同**；日志中**无** `Network: 41ms` 直采行
3. **对局 5ms**：进局后游戏显示到**对战服**的 RTT（用户截图 5ms），与大厅 41ms 属**游戏内不同阶段指标**；全程系统 Ping 仍 **3~7ms**，**无 WiFi 断连/质量策略误杀**
4. **WiFi 排除**：37 次 `WifiNetworkCheck` Ping 全 `success=true`；`WifiNetworkQuality: rssi sufficient` + `tput greater than NO_INTERNET_TRAFFIC`；无 `isHighPingDelay`、无 `tear down wlan0`；IP **192.168.100.95/24**，链路 **351Mbps**

与 CASE-006/008 区别：本单**强信号、无 PER 持续劣化/断连**；与 CASE-012 类似：系统 WiFi 正常而用户感知「应用延迟高」，但本单为**游戏 UI 分阶段延迟显示**，非 App 报网络不可用。

**日志局限**：Wild Rift 使用 GCloud/MSDK（`libgcloud.so`、`GPMSDK`），大厅/对局具体 ping 目标 IP **未写入 main log**；`GCloudSDKLog/GPMSDK_*.log` 未进 TagLog。要 log 级坐实「大厅/对局不同服务器」需补抓 GCloud 日志或 tcpdump。

## 排查步骤

### 第一步：排除 WiFi（本案例可快速闭环）
1. main_log 搜 `WifiNetworkCheck` **Ping** → 是否 **3~20ms 且 success=true**（对应用户「3ms 测试」）
2. 对照同分钟 **Probe** → 是否 **几十~几百 ms**、`response=204`（证明 Ping/Probe 为不同探测层级）
3. 搜 `DISCONNECTED` / `network lost` / `tear down wlan0` → 应为 **0**
4. `TranWifiSmartAssistantController: ====>>rssi` → 是否持续优良（如 >-55 dBm）
5. `WifiNetworkQuality` → 是否 `rssi sufficient` + `tput greater than NO_INTERNET_TRAFFIC`

### 第二步：对齐用户截图与游戏阶段
1. 向用户确认 **41ms 是否来自大厅 PLAY 前界面**、**5ms 是否来自对局内**
2. main_log 搜 `com.riotgames.league.wildrift`：`queueBuffer fps` 大厅约 **30fps**、对局约 **60fps**（间接区分阶段）
3. 搜 `GPMSDK` / `GCloud`：`[ACTIVE]` / `[WAIT TO ACTIVE]` 可对齐进局时刻，但**不含 RTT 数值**

### 第三步：鉴别「真 WiFi 高延迟」vs「测量对象不同」
| 若 WiFi 真有问题 | 本单实际 |
|------------------|----------|
| 系统 Ping 同步升高（>50ms 或 fail） | Ping 全程 3~17ms success |
| RSSI 差 / PER 持续高 / 断连 | RSSI -44~-53，无断连 |
| 游戏延迟与系统 Ping 同向恶化 | 大厅 41ms 时系统 Ping 仍 3~6ms |

### 第四步：深入取证（可选，转游戏侧）
1. 补抓 `Android/data/com.riotgames.league.wildrift/cache/GCloudSDKLog/`
2. 大厅 vs 对局各抓 **tcpdump**，对比 UDP 目标 IP 是否变化
3. 同网络 `ping 192.168.x.1`（~3ms）vs `ping 8.8.8.8`（几十 ms）帮助用户理解差异

## 关键日志

```
// 系统近端 Ping（与用户 3ms 测试一致）
06-28 16:01:09  WifiStatistics:WifiNetworkCheck: Ping result: {success=true, time=3ms}
06-28 16:46:10  WifiStatistics:WifiNetworkCheck: Ping result: {success=true, time=15ms}

// 同模块公网 Probe（证明 Ping≠公网 RTT）
06-28 16:00:39  WifiStatistics:WifiNetworkCheck: Ping result: {success=true, time=5ms}
06-28 16:00:39  WifiStatistics:WifiNetworkCheck: Probe result: {success=true, time=68ms, response=204}
06-28 16:01:39  WifiStatistics:WifiNetworkCheck: Probe result: {success=true, time=208ms, response=204}

// WiFi 链路优良（问题时刻附近）
06-28 16:45:16  Network capabilities: VALIDATED ... NOT_CONGESTED ... RSSI: -52, Link speed: 351Mbps
06-28 16:45:25  WifiNetworkQuality: current rssi is sufficient
06-28 16:45:25  WifiNetworkQuality: tput greater than NO_INTERNET_TRAFFIC
06-28 16:45:25  TranWifiSmartAssistantController: SSID "Boss_atan5gzh", rssi:-52

// 局域网 IP
06-28 16:00:13  netd: interfaceGetCfg(wlan0) -> ipv4Addr: 192.168.100.95, prefixLength: 24

// 游戏网络栈（无 RTT 直采）
06-28 16:00:53  GCloudCore: loadLibrary:libMSDKPIXCore.so / libgcloud.so
06-28 16:00:40  GPMSDK: Open log file: .../GCloudSDKLog/GPMSDK/GPMSDK_2026062816.log

// 阶段间接证据：大厅 ~30fps → 对局 ~60fps
06-28 15:59:54  wildrift SurfaceView queueBuffer: fps=29.99
06-28 16:29:xx  wildrift SurfaceView queueBuffer: fps=59.8~60.0
```

## 建议措施

### WiFi 模块
- 闭环结论：**WiFi 网速/时延/连接无异常**，建议 **Non-WiFi / 用户说明 / 转第三方游戏**
- Jira 回复可附：系统 Ping 3~7ms + 截图大厅 41ms + 对局 5ms 对照表

### 用户沟通话术
- WiFi 测试 3ms = 到路由器；游戏大厅 41ms = 到游戏平台服务器；对局 5ms = 到对战服——**三者不可直接对比**
- 41ms 在菲律宾访问国际游戏基础设施属常见范围，不代表 WiFi 故障

### 三方 / 游戏（若需继续跟）
- 向 Riot/腾讯确认大厅 `Network: xx ms` 与对局右上角 ping 的探测目标与算法差异
- 补 GCloudSDK 日志或 tcpdump 坐实服务器选路

## TAG
- Wild Rift
- league.wildrift
- 应用层延迟显示
- WifiNetworkCheck
- Ping与Probe分层
- 强信号
- 无断开
- GCloud
- GPMSDK
- 粉丝反馈
- 菲律宾
- CN6
- MTK平台
- 非WiFi问题

## 相关案例
- **CASE-012**（TOS163-35222）：系统 WiFi Ping/Probe 正常但 App 层网络感知异常 — 鉴别「系统正常 vs 应用显示」思路类似
- **CASE-017**（X6878OS16-11111）：强 WiFi 下第三方 App 问题 — WiFi 快速排除流程可参考
- **CASE-019**（TOS163-37795）：Probe 打 `connectivitycheck.gstatic.com`、Ping 为网关级 — 解释 Ping/Probe 分层
- **CASE-006/008**：弱信号/PER 高导致游戏卡顿 — 本单**不匹配**

## 分析报告
- `AI-result/issues/CN6OS16-2171/CN6OS16-2171-analysis.md`
- 链路质量图：`AI-result/issues/CN6OS16-2171/CN6OS16-2171_link_quality.png`
