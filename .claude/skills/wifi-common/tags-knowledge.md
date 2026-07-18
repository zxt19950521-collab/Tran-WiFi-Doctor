# WiFi 问题 TAG 知识库

## TAG 分类体系

### 1. P2P 连接类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| P2P冲突 | WiFi Direct P2P连接过程中发生冲突 | `p2p Conflict`, `P2P-GROUP-FORMATION-FAILURE` | P2P连接失败 |
| GC超时 | GC加入GO超时（10秒） | `GC未加入`, `10秒超时`, `P2PGoCreatedEvent.*unregister` | P2P连接失败 |
| P2P超时 | P2P连接整体超时 | `WIFI_P2P_TIMEOUT`, `notifyConnectFail` | P2P连接失败 |
| GC扫描失败 | GC无法扫描到GO | `GC扫描失败`, `P2P-DEVICE-FOUND` 未出现 | P2P连接失败 |
| P2P连接成功 | P2P链路建立成功 | `P2P-GROUP-STARTED`, `Key negotiation completed` | 业务层失败 |
| 4次握手成功 | WPA 4次握手完成 | `Key negotiation completed [PTK=CCMP GTK=CCMP]` | DHCP失败 |
| Group Formation超时 | P2P组群形成阶段超时 | `P2P: Group Formation timed out`, `P2P-GROUP-FORMATION-FAILURE` | P2P连接失败 |
| 建链后秒断 | RSNA完成后极短时间被踢 | `NL80211_CMD_DISCONNECT`, `CTRL-EVENT-DISCONNECTED reason=0` | P2P连接失败 |
| 应用层MAC/握手 | L7业务校验失败 | `deviceMac not match`, `dealConnectResult` | 业务失败 |
| EAPOL MIC失败 | EAPOL密钥校验失败 | `Invalid EAPOL-Key MIC - dropping packet` | 认证失败 |

### 2. DHCP 类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| DHCP失败 | DHCP获取IP地址失败 | `DHCP timeout`, `Failed to get DHCP lease` | 业务失败 |
| DHCP超时 | DHCP请求超时 | `DHCP REQUEST` 重传多次无ACK | 业务失败 |
| DHCP REQUEST无ACK | GO端未回复DHCP ACK | `DHCP: Send REQUEST` 重传4次 | IP地址未分配 |
| DHCP NAK | DHCP服务器拒绝请求 | `Received DHCPNAK` | DHCP失败 |
| DHCP DECLINE | 客户端拒绝DHCP Offer | `Sending DHCPDECLINE` | DHCP失败 |
| IP配置丢失 | IP配置丢失 | `CMD_IP_CONFIGURATION_LOST` | 断开连接 |
| 配置失败 | IP配置失败 | `IpClient: onProvisioningFailure` | DHCP失败 |
| APF ENOSYS | P2P接口不支持APF | `getApfCapabilities failed: ENOSYS` | IpClient初始化失败 |
| DhcpClient ILLEGAL ARGUMENT | DhcpClient初始化参数错误 | `Error retrieving network attributes: ILLEGAL ARGUMENT` | DHCP失败 |
| IpClient初始化失败 | IpClient无法初始化 | `IpClient.p2p0: ERROR` | DHCP失败 |
| IP地址未配置 | IP地址未配置到接口 | 无 `interfaceSetCfg` 日志 | 业务失败 |
| Kernel DHCP成功 | 内核层DHCP四步握手成功 | `Dhcp done, stop GC join timer` | 框架层失败 |
| DHCP租约过期 | DHCP租约到期 | `lease expired` | 断开连接 |

### 3. 认证类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| 认证失败 | WiFi认证失败 | `CTRL-EVENT-DISCONNECTED reason=2`, `Authentication failure` | 连接失败 |
| 密钥错误 | WPA密钥不匹配 | `WPA: 4-Way Handshake failed` | 认证失败 |
| PSK不匹配 | 预共享密钥错误 | `CTRL-EVENT-DISCONNECTED reason=2`, `PREV_AUTH_NOT_VALID` | 认证失败 |
| EAP失败 | EAP认证失败 | `CTRL-EVENT-EAP-FAILURE`, `EAP-TLS: TLS processing failed` | 认证失败 |
| WPA3/SAE失败 | WPA3 SAE认证失败 | `SAE: authentication failure` | 认证失败 |
| 关联拒绝 | AP拒绝关联请求 | `CTRL-EVENT-ASSOC-REJECT ... status_code=<N>` | 连接失败 |
| 关联超时 | 关联请求超时 | `CTRL-EVENT-SSID-TEMP-DISABLED ... auth_failures=<N>` | 连接失败 |
| 4次握手失败 | WPA 4次握手失败 | `WPA: 4-Way Handshake failed`, `CTRL-EVENT-DISCONNECTED reason=15` | 认证失败 |
| 组密钥握手超时 | 组密钥握手超时 | `CTRL-EVENT-DISCONNECTED reason=16` | 断开连接 |

### 4. 扫描类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| 扫描失败 | WiFi扫描失败 | `Scan failed`, `SCAN-FAILED` | 连接失败 |
| 扫描超时 | WiFi扫描超时 | `Scan timeout` | 连接失败 |
| PNO扫描失败 | 后台扫描失败 | `Failed to start PNO scan` | 连接失败 |
| 扫描节流 | 扫描请求被节流 | `Scan request throttled` | 连接延迟 |
| 未找到网络 | 扫描后未找到目标网络 | `connectToNetwork: Cannot find network`, `No candidates selected` | 连接失败 |
| WificondScannerImpl失败 | wificond扫描启动失败 | `WificondScannerImpl: Failed to start scan`, `status: -9` | 扫描失败 |

### 5. 断开连接类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| 断开连接 | WiFi连接断开 | `CTRL-EVENT-DISCONNECTED` | 业务中断 |
| 信号弱 | 信号强度过低 | `RSSI` 低于阈值 | 断开连接 |
| 漫游失败 | AP间漫游失败 | `Roaming failed` | 断开连接 |
| 过度漫游 | 短时间内多次漫游 | `Multiple BSSID changes detected in short window` | 性能问题 |
| BSSID黑名单 | BSSID被加入黑名单 | `BSSID blacklisted`, `Filtered out BSSID` | 连接失败 |
| 固件崩溃 | WiFi固件崩溃 | `SSR`, `subsystem restart`, `firmware crash` | 断开连接 |
| AP发起解认证 | AP端主动断开 | `locally_generated=0 reason=3` | 断开连接 |
| 网关不可达 | 默认网关不可达 | `IpReachabilityMonitor: FAILURE`, `Lost default router` | 断开连接 |
| Doze模式断开 | 省电模式导致断开 | `DeviceIdle ... IDLE` 后断开 | 断开连接 |
| 不活动解除关联 | 长时间不活动被踢 | `CTRL-EVENT-DISCONNECTED reason=4` | 断开连接 |
| WifiNetworkQuality断连 | 网络质量策略触发扫描后拆除wlan0 | `isHighPingDelay : true`, `start scan !`, `torn down Iface.*wlan0` | 断开连接 |
| wlan0 tear down | 框架主动拆除STA接口 | `Successfully torn down Iface:{Name=wlan0` | 断开连接 |
| 应用层网络误报 | App报不可用但系统WiFi正常 | `SBE: this page is abnormal implementation` | 业务失败 |
| 截图时刻PER正常 | 截图时刻kernel PER≤10%排除空口问题 | `wlanLinkQualityMonitor ... PER(0)` ~ `PER(10)` | 鉴别应用层误报 |

### 6. DNS/网络验证类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| DNS超时 | DNS查询超时 | `DnsResolver: DNS query timeout` | 网络不可用 |
| DNS解析失败 | DNS解析失败 | `NetworkMonitor: DNS resolution failed` | 网络不可用 |
| 网络验证失败 | 网络连通性验证失败 | `HTTPS probe failed` | 网络不可用 |
| 强制门户 | 检测到强制门户 | `Captive portal detected` | 网络受限 |
| 无互联网 | 网络无互联网访问 | `Network has no internet access` | 网络不可用 |
| Update score for net | ConnectivityService 更新选网打分（管家关键字） | `ConnectivityService: Update score for net` | 默认网/感叹号 |
| Update capabilities for net | ConnectivityService 更新网络能力（管家关键字） | `ConnectivityService: Update capabilities for net` | App 可见上网能力 |
| TRANSPORT_PRIMARY主传输通道 | score 将该 net 选为**主传输/默认网候选** | `Update score for net.*+TRANSPORT_PRIMARY` | 已当主网≠已验证上网 |
| YIELD_TO_BAD_WIFI对坏WiFi让步 | 对糟糕 WiFi 让步，常打在**蜂窝** score 上 | `Update score for net.*YIELD_TO_BAD_WIFI` | 坏 WiFi 时流量救场 |
| IS_VALIDATED当前已验证 | **此刻**能否真正上网的黄金标准 | `+IS_VALIDATED` / `-IS_VALIDATED` | 通网 / 感叹号 |
| EVER_VALIDATED曾经验证过 | 历史曾验证通过的“良民证” | `+EVER_VALIDATED` | 暂时不通时更宽容 |
| 网络波动短暂失验恢复 | 同一 net 短暂断流后自动恢复 | `-VALIDATED+PARTIAL` → 数秒后 `-PARTIAL+VALIDATED` | 视频转圈后自愈 |
| 网络已验证可上网 | score/capabilities 标记已验证 | `+EVER_EVALUATED` / `+IS_VALIDATED` / `+VALIDATED` | 可上网 |
| 网络未验证感叹号 | 失去验证或尚未完成验证 | `-IS_VALIDATED` / `-VALIDATED` | 状态栏感叹号 |
| 部分连通PARTIAL_CONNECTIVITY | capabilities 半通（常伴 -VALIDATED） | `+PARTIAL_CONNECTIVITY` | 有时能用/App 失败 |
| capabilities强制门户CAPTIVE_PORTAL | capabilities 判门户且无 VALIDATED | `+CAPTIVE_PORTAL` | 网络受限；须定传输侧 |
| networkAddInterface定传输侧 | netd 将 netId 绑定网卡，据此区分 WiFi/蜂窝 | `netd: networkAddInterface(<netId>, <ifName>)` | 确认 score/capabilities 所属传输侧 |

### 7. 性能类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| 吞吐量低 | WiFi吞吐量低 | `throughput` 低于预期, `Tput:` 低值 | 性能问题 |
| 延迟高 | WiFi延迟高 | `latency` 高于阈值 | 性能问题 |
| 丢包 | WiFi丢包率高 | `packet loss`, `PER(` 高值 | 性能问题 |
| 通道拥塞 | 信道拥堵 | 同信道多BSSID | 性能问题 |
| 省电模式激进 | 省电策略过于激进 | 屏幕关闭后延迟飙升 | 性能问题 |
| 热节流 | 热节流导致性能下降 | `thermal throttling` | 性能问题 |
| RSSI低 | 信号强度低 | `mtk_cfg80211_get_station ... rssi=` 低值 | 性能问题 |
| 协商速率低 | WiFi协商速率低 | `wlanLinkQualityMonitor ... Tx(rate:` 低值 | 性能问题 |

### 8. 平台/设备类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| MTK平台 | 联发科芯片平台 | `MTK`, `mtk` | 平台特定问题 |
| MTK driver | MTK驱动问题 | `mtk_wifi`, `wmt_drv`, `wlan`, `wcn` | 驱动问题 |
| CN5c | TECNO CN5c设备 | 设备型号标识 | 设备特定问题 |
| Windows | Windows PC端 | `Windows`, `PC` | 平台特定问题 |
| 极速互传 | 极速互传业务 | `AirTransfer`, `极速互传` | 业务问题 |

### 9. 环境类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| SCC同信道 | STA和P2P同信道 | `SCC`, `same channel` | 干扰问题 |
| AP密集 | 周围AP密集 | 多个AP信号 | 干扰问题 |
| 2.4G频段 | 2.4GHz频段 | `freq=2412`, `2.4G` | 频段问题 |
| 5G频段 | 5GHz频段 | `freq=5180`, `5G` | 频段问题 |

### 10. 系统事件类

| TAG | 描述 | 典型日志模式 | 关联问题 |
|-----|------|-------------|----------|
| 屏幕状态变化 | 屏幕开启/关闭 | `screen on`, `screen off` | 省电相关 |
| Doze模式 | 设备进入Doze省电模式 | `DeviceIdle`, `IDLE` | 断开连接 |
| 飞行模式 | 飞行模式开启/关闭 | `airplane mode` | 连接中断 |
| 热事件 | 设备过热 | `thermal`, `temperature` | 性能问题 |
| 内存压力 | 系统内存压力大 | `low memory`, `memory pressure` | 性能问题 |
| SystemUI发起连接 | 系统框架/SystemUI 代发 WiFi 连接 | `WifiService: connect.*packageNameToUse=com.android.systemui` | 自动选网/连通性恢复 |
| 用户设置发起连接 | 用户在设置中手动连接 WiFi | `WifiService: connect.*packageNameToUse=com.android.settings` | 用户操作 |

## 框架连接日志解读（WifiService: connect）

分析 **SSID 切换 / 重连 / network lost** 时，必须结合 `WifiService: connect` 判断**谁发起了连接**，避免把框架自动切网误判为用户手动操作。

### 日志格式

```
WifiService: connect uid=<调用方uid> uidToUse=<实际uid> packageNameToUse=<包名> attributionTagToUse=<tag>
```

| 字段 | 含义 |
|------|------|
| `WifiService: connect` | 有一次 WiFi 连接请求（connectToNetwork 入口） |
| `uid` / `uidToUse` | 发起连接的应用 UID |
| `packageNameToUse` | **发起连接的应用包名**（分析重点） |

### 常见 packageNameToUse 对照

| packageNameToUse | 含义 | 分析注意 |
|------------------|------|----------|
| `com.android.systemui` | **SystemUI / 系统框架代发** | 常见于 TranWifiSmartAssistant 自动选网、no-internet 恢复、连通性策略触发的重连；**不等于用户在 WiFi 列表手动点击** |
| `com.android.settings` | **设置应用发起** | 通常为用户在 WiFi 设置页手动选择/连接网络 |
| 其他第三方包名 | 对应应用发起 | 如游戏/工具调用系统 API 请求连接特定网络 |

### 分析要点

1. 出现 `network lost` 或 SSID 切换后，**向前搜索**同时间窗内的 `WifiService: connect`，确认发起方。
2. 若多次切换均为 `com.android.systemui`，优先排查 **框架自动选网 / Probe 失败 / SmartAssistant** 链路，而非用户误操作。
3. 与 `wpa_supplicant: CTRL-EVENT-CONNECTED` / `DISCONNECTED` 时间对齐，可还原完整「谁发起 → 关联 → 断连」链条。

### 参考案例

- **TOS163-37795**：Probe 失败后 SSID 乒乓，`WifiService: connect` 均为 `com.android.systemui`。

## 网络验证状态日志解读（ConnectivityService: Update score / Update capabilities）

判断网络 **是否已验证可上网**、状态栏是否显示**感叹号**，必须同时检索两行管家关键字：

| 关键字 TAG | 改什么 | 看行末标记 |
|------------|--------|------------|
| **Update score for net** | 选网打分（谁当默认网） | `IS_VALIDATED` / `EVER_EVALUATED` / `TRANSPORT_PRIMARY` … |
| **Update capabilities for net** | 网络能力（给 App/UI） | `VALIDATED` / `PARTIAL_CONNECTIVITY` / `CAPTIVE_PORTAL` … |

常见时序：**capabilities 先变 → score 毫秒级跟随**。

### 日志格式

```
ConnectivityService: Update capabilities for net <networkId> : <能力标记>
ConnectivityService: Update score for net <networkId> : <score标记>
```

### score 判定规则

| 行末 score 标记 | 含义 | 状态栏 |
|----------------|------|--------|
| 含 **`+EVER_EVALUATED`** | 探测流程已跑完（须再看 capabilities 是否 `+VALIDATED`） | 视 capabilities |
| 含 **`+IS_VALIDATED`** | **此刻**探测通过、可真正上网（黄金标准） | 正常（无感叹号） |
| 含 **`+EVER_VALIDATED`** | **曾经**验证通过过（历史良民证）；可与当前 `-IS_VALIDATED` 并存 | 当前仍可能感叹号 |
| 含 **`-IS_VALIDATED`** | **当前**失去验证（不等于从未通过） | **感叹号** |
| 含 **`+TRANSPORT_PRIMARY`** | 该 net 被选为**主传输通道/默认网候选** | 此时若尚未 VALIDATED → **感叹号** |
| 含 **`+YIELD_TO_BAD_WIFI`** | 对糟糕 WiFi **让步**；多见于**蜂窝** score，允许流量临时顶上 | 视谁是 default |
| 仅有 `+IS_UNMETERED` / `+TRANSPORT_PRIMARY` 等，**无 EVER_EVALUATED/VALIDATED** | 已当主网但尚未完成验证，**不可上网** | **感叹号** |

> 注意：`+TRANSPORT_PRIMARY` / `+EVER_EVALUATED` **都不等于**可上网；须看 `+IS_VALIDATED` 或 capabilities `+VALIDATED`。`EVER_EVALUATED`≠`EVER_VALIDATED`。

### 认识 → 信任：关键 score 标签组合

从“刚认识”到“信任/救场”，常用组合：

| 阶段 | 典型标记 | 通俗含义 |
|------|----------|----------|
| 刚连上 | `+TRANSPORT_PRIMARY`，尚无 `IS_VALIDATED` | 已当主网候选，还在探测 |
| 首次探测成功 | `+EVER_EVALUATED` + `+EVER_VALIDATED` + `+IS_VALIDATED` | 现在通，且记入历史良民 |
| 短暂掉线 | `-IS_VALIDATED`，**仍保留** `EVER_VALIDATED` | 现在不通，但曾证明过，先宽容等待 |
| 判定坏 WiFi，流量救场 | 蜂窝 net 上 `+YIELD_TO_BAD_WIFI`（常伴 `TRANSPORT_PRIMARY`） | WiFi 太烂，移动数据临时顶上 |

**勿混淆**：

| 标记 | 含义 |
|------|------|
| `EVER_EVALUATED` | 探测**流程跑完**（结果可能是 VALIDATED / CAPTIVE / 失败） |
| `EVER_VALIDATED` | **曾经验证通过过**（历史良民） |
| `IS_VALIDATED` | **当前**验证通过 |

### capabilities 判定规则

| 行末 capabilities 标记 | 含义 |
|------------------------|------|
| **`+VALIDATED`** | 已验证可上网（常紧跟 score `+IS_VALIDATED`） |
| **`-VALIDATED+PARTIAL_CONNECTIVITY`** | **部分连通/半通**（Ping 可能 OK，HTTP(S) 探测差） |
| **`-PARTIAL_CONNECTIVITY+VALIDATED`** | 从半通恢复为已验证 |
| **`+CAPTIVE_PORTAL`**（无 `+VALIDATED`） | 探测判门户/拦截；**必须用 networkAddInterface 定 WiFi/蜂窝侧** |

### 分析要点

1. 每次 SSID 切换会产生新的 `net <id>`，通常先 `+TRANSPORT_PRIMARY`，数秒～数十秒后才 `+VALIDATED`；此窗口内用户可见感叹号。
2. 同一 netId 上 `VALIDATED ↔ PARTIAL_CONNECTIVITY` 往返 = 间歇半通 / 网络波动，对齐 OEM Probe 失败 + Ping 成功。
3. 与 `Wifi network validated` / `unvalidated` / `no-internet access` 时间对齐。
4. 出现 score/capabilities 后，用 **networkAddInterface** 确认传输侧。

### 典型时间线：短暂断流又自动恢复（同一 netId）

日常最常见的「网络波动」底层写照。系统路径：**发现断网 → 持续探测 → 确认恢复**。因常带 `EVER_VALIDATED`，中间数秒～数十秒**不会立刻踢网**。

| 时刻 | 日志 | 含义 | 用户体感 |
|------|------|------|----------|
| T0 | capabilities `-VALIDATED+PARTIAL_CONNECTIVITY` | 半通：多半只能到路由器，上不了真正外网 | — |
| T0（毫秒后） | score `-IS_VALIDATED` | 拔掉「此刻畅通」标签，扣分 | 视频转圈、消息发不出 |
| T0～T1 | （后台重发探测；常保留 `EVER_VALIDATED`） | 宽容等待，不立刻切走 | 短暂卡顿 |
| T1 | capabilities `-PARTIAL_CONNECTIVITY+VALIDATED` | 去掉半通，重新颁发上网认证 | 视频续播、消息发出 |
| T1（毫秒后） | score `+IS_VALIDATED` | 恢复「此刻畅通」 | 恢复正常 |

**实例（X6885OS16-533 net 212，约 13s）**：

```
07:16:00  Update capabilities ... -VALIDATED+PARTIAL_CONNECTIVITY
07:16:00  Update score ... -IS_VALIDATED
07:16:13  Update capabilities ... -PARTIAL_CONNECTIVITY+VALIDATED
07:16:13  Update score ... +IS_VALIDATED
```

同单此前 `07:13:35`～`07:13:41`（约 6s）为同构一次波动。

### 参考案例

- **TOS163-37795**：
  - `12:56:43` net 183 `: -IS_VALIDATED` → 感叹号
  - `12:56:53` net 184 先 `+TRANSPORT_PRIMARY`，`12:57:02` 才 `+EVER_EVALUATED`
  - `12:58:55` net 191 `: +EVER_VALIDATED+IS_VALIDATED` → 恢复可上网
- **X6885OS16-533**：
  - net 212：两次「短暂失验恢复」（`07:13:35`～`41`、`07:16:00`～`13`）
  - net 213/217（wlan0）：正常 `+VALIDATED` / `+IS_VALIDATED`
  - net 214/215/216（ccmni）：`+YIELD_TO_BAD_WIFI`（对坏 WiFi 让步、蜂窝救场）；214/215 另见 `+CAPTIVE_PORTAL`

## netId 传输侧判定（netd: networkAddInterface）

出现 `ConnectivityService: Update score/capabilities for net <id>` 后，必须用 **`networkAddInterface`** 确认该 netId 绑的是哪张网卡，避免把蜂窝网的 `CAPTIVE_PORTAL` / `YIELD_TO_BAD_WIFI` 误判为 WiFi 问题。

### 日志格式

```
netd: networkAddInterface(<netId>, <ifName>)
```

### ifName 对照

| ifName | 传输侧 |
|--------|--------|
| `wlan0` | **WiFi** STA |
| `ccmni*` / `rmnet*` | **蜂窝**（MTK 常用 `ccmni0/1/...`） |
| `p2p0` | **P2P** |
| `ap0` / `wlan1`（视平台） | SoftAP / 辅接口，需结合上下文 |

### 分析要点

1. 对每个出现 score/capabilities 的 `net <id>`，检索同时间窗 `networkAddInterface(<id>,`。
2. 双网并存时（开移动数据后），WiFi 与蜂窝各自有不同 netId；capabilities 结论必须按 ifName 归侧。
3. 辅助旁证：WiFi 建网常先 `+IS_UNMETERED`；蜂窝常出现 `YIELD_TO_BAD_WIFI`；DNS 为运营商地址而非 `192.168.x.1`。以 **ifName 为准**。

### 参考案例

- **X6885OS16-533**：net 213 → `wlan0`；net 214 → `ccmni0`；net 215 → `ccmni1`（用户开蜂窝后出现 `+CAPTIVE_PORTAL`）。

## 断开原因代码速查

| 代码 | 含义 | 对应TAG |
|-----:|------|---------|
| 0 | 未指定原因 | 建链后秒断 |
| 2 | 之前的认证不再有效 | PSK不匹配, 认证失败 |
| 3 | 站点离开而解认证 | AP发起解认证 |
| 4 | 不活动而解除关联 | 不活动解除关联 |
| 15 | 4次握手超时 | 4次握手失败 |
| 16 | 组密钥握手超时 | 组密钥握手超时 |

## TAG 提取规则

### 自动提取模式

```json
{
  "P2P冲突": ["p2p Conflict", "_onDisconnected.*Conflict", "P2P-GROUP-FORMATION-FAILURE"],
  "GC超时": ["GC未加入", "10秒超时", "P2PGoCreatedEvent.*unregister"],
  "P2P超时": ["WIFI_P2P_TIMEOUT", "notifyConnectFail"],
  "Group Formation超时": ["P2P: Group Formation timed out", "P2P-GROUP-FORMATION-FAILURE"],
  "建链后秒断": ["NL80211_CMD_DISCONNECT", "CTRL-EVENT-DISCONNECTED reason=0"],
  "应用层MAC/握手": ["deviceMac not match", "dealConnectResult"],
  "EAPOL MIC失败": ["Invalid EAPOL-Key MIC - dropping packet"],
  "DHCP失败": ["DHCP timeout", "Failed to get DHCP lease", "No DHCPOFFER received"],
  "DHCP超时": ["DHCP REQUEST.*重传", "未收到ACK"],
  "DHCP REQUEST无ACK": ["DHCP: Send REQUEST.*重传", "未收到ACK"],
  "DHCP NAK": ["Received DHCPNAK"],
  "DHCP DECLINE": ["Sending DHCPDECLINE"],
  "IP配置丢失": ["CMD_IP_CONFIGURATION_LOST"],
  "配置失败": ["IpClient: onProvisioningFailure"],
  "APF ENOSYS": ["getApfCapabilities failed: ENOSYS"],
  "DhcpClient ILLEGAL ARGUMENT": ["Error retrieving network attributes: ILLEGAL ARGUMENT"],
  "IpClient初始化失败": ["IpClient.*ERROR", "Cannot get APF capabilities"],
  "DHCP租约过期": ["lease expired"],
  "认证失败": ["CTRL-EVENT-DISCONNECTED reason=2", "Authentication failure", "SupplicantStateTracker: Authentication failure"],
  "密钥错误": ["WPA: 4-Way Handshake failed"],
  "PSK不匹配": ["CTRL-EVENT-DISCONNECTED reason=2", "PREV_AUTH_NOT_VALID"],
  "EAP失败": ["CTRL-EVENT-EAP-FAILURE", "EAP-TLS: TLS processing failed"],
  "WPA3/SAE失败": ["SAE: authentication failure"],
  "关联拒绝": ["CTRL-EVENT-ASSOC-REJECT.*status_code="],
  "关联超时": ["CTRL-EVENT-SSID-TEMP-DISABLED.*auth_failures=", "Timed out waiting for supplicant state change", "CMD_CONNECTING_WATCHDOG_TIMER"],
  "4次握手失败": ["WPA: 4-Way Handshake failed", "CTRL-EVENT-DISCONNECTED reason=15"],
  "组密钥握手超时": ["CTRL-EVENT-DISCONNECTED reason=16"],
  "扫描失败": ["Scan failed", "getScanResults failed", "SCAN-FAILED"],
  "PNO扫描失败": ["Failed to start PNO scan"],
  "扫描节流": ["Scan request throttled"],
  "未找到网络": ["connectToNetwork: Cannot find network", "No candidates selected"],
  "断开连接": ["CTRL-EVENT-DISCONNECTED"],
  "信号弱": ["RSSI.*低", "signal.*weak"],
  "漫游失败": ["Roaming failed", "ROAMING-FAILED"],
  "过度漫游": ["Multiple BSSID changes detected in short window"],
  "BSSID黑名单": ["BSSID blacklisted", "Filtered out BSSID"],
  "固件崩溃": ["SSR", "subsystem restart", "firmware crash"],
  "AP发起解认证": ["locally_generated=0 reason=3"],
  "网关不可达": ["IpReachabilityMonitor: FAILURE", "Lost default router"],
  "Doze模式断开": ["DeviceIdle.*IDLE"],
  "不活动解除关联": ["CTRL-EVENT-DISCONNECTED reason=4"],
  "WifiNetworkQuality断连": ["isHighPingDelay : true", "WifiNetworkQuality: start scan", "torn down Iface.*wlan0"],
  "wlan0 tear down": ["Successfully torn down Iface.*wlan0", "Type=STA_CONNECTIVITY"],
  "WificondScannerImpl失败": ["WificondScannerImpl: Failed to start scan", "status: -9"],
  "应用层网络误报": ["SBE.*abnormal implementation", "this page is abnormal implementation"],
  "network lost": ["Wifi network lost", "WifiNetworkCheck: Wifi network lost"],
  "DNS超时": ["DnsResolver: DNS query timeout"],
  "DNS解析失败": ["NetworkMonitor: DNS resolution failed"],
  "网络验证失败": ["HTTPS probe failed"],
  "强制门户": ["Captive portal detected"],
  "无互联网": ["Network has no internet access"],
  "吞吐量低": ["Tput:", "throughput.*低"],
  "延迟高": ["latency.*高"],
  "丢包": ["packet loss", "PER("],
  "通道拥塞": ["同信道多BSSID"],
  "省电模式激进": ["屏幕关闭后延迟飙升"],
  "热节流": ["thermal throttling"],
  "RSSI低": ["mtk_cfg80211_get_station.*rssi=.*-[0-9]{2,}"],
  "协商速率低": ["wlanLinkQualityMonitor.*Tx(rate:.*[0-9]+ Mbps"],
  "屏幕状态变化": ["screen on", "screen off"],
  "Doze模式": ["DeviceIdle", "IDLE"],
  "飞行模式": ["airplane mode"],
  "热事件": ["thermal", "temperature"],
  "内存压力": ["low memory", "memory pressure"],
  "SystemUI发起连接": ["WifiService: connect.*packageNameToUse=com.android.systemui"],
  "用户设置发起连接": ["WifiService: connect.*packageNameToUse=com.android.settings"],
  "Update score for net": ["ConnectivityService: Update score for net"],
  "Update capabilities for net": ["ConnectivityService: Update capabilities for net"],
  "网络已验证可上网": [
    "ConnectivityService: Update score for net.*\\+EVER_EVALUATED",
    "ConnectivityService: Update score for net.*\\+IS_VALIDATED",
    "ConnectivityService: Update capabilities for net.*\\+VALIDATED"
  ],
  "网络未验证感叹号": [
    "ConnectivityService: Update score for net.*-IS_VALIDATED",
    "ConnectivityService: Update capabilities for net.*-VALIDATED"
  ],
  "部分连通PARTIAL_CONNECTIVITY": ["ConnectivityService: Update capabilities for net.*PARTIAL_CONNECTIVITY"],
  "capabilities强制门户CAPTIVE_PORTAL": ["ConnectivityService: Update capabilities for net.*CAPTIVE_PORTAL"],
  "TRANSPORT_PRIMARY主传输通道": ["ConnectivityService: Update score for net.*\\+TRANSPORT_PRIMARY"],
  "YIELD_TO_BAD_WIFI对坏WiFi让步": ["ConnectivityService: Update score for net.*YIELD_TO_BAD_WIFI"],
  "IS_VALIDATED当前已验证": [
    "ConnectivityService: Update score for net.*\\+IS_VALIDATED",
    "ConnectivityService: Update score for net.*-IS_VALIDATED"
  ],
  "EVER_VALIDATED曾经验证过": ["ConnectivityService: Update score for net.*\\+EVER_VALIDATED"],
  "网络波动短暂失验恢复": [
    "ConnectivityService: Update capabilities for net.*-PARTIAL_CONNECTIVITY\\+VALIDATED",
    "ConnectivityService: Update capabilities for net.*-VALIDATED\\+PARTIAL_CONNECTIVITY"
  ],
  "networkAddInterface定传输侧": ["netd.*networkAddInterface", "networkAddInterface\\(\\d+,\\s*wlan0\\)", "networkAddInterface\\(\\d+,\\s*ccmni", "networkAddInterface\\(\\d+,\\s*rmnet", "networkAddInterface\\(\\d+,\\s*p2p0\\)"]
}
```

## TAG 关联分析

### 典型问题链条

1. **P2P连接成功后业务失败**
   ```
   P2P连接成功 → 4次握手成功 → DHCP失败 → IP地址未配置 → 业务失败
   ```
   - 关键TAG: P2P连接成功, 4次握手成功, DHCP失败, IP地址未配置
   - 典型案例: CASE-003

2. **P2P连接阶段失败**
   ```
   P2P发起 → GC扫描失败 → GC超时 → P2P超时 → 连接失败
   ```
   - 关键TAG: GC扫描失败, GC超时, P2P超时
   - 典型案例: CASE-002

3. **P2P冲突导致失败**
   ```
   P2P连接 → P2P冲突 → 断开连接 → 连接失败
   ```
   - 关键TAG: P2P冲突, 断开连接
   - 典型案例: CASE-001

4. **Group Formation超时**
   ```
   P2P发起 → Group Formation超时 → P2P-GROUP-FORMATION-FAILURE → 连接失败
   ```
   - 关键TAG: Group Formation超时, P2P超时
   - 典型案例: 待补充

5. **建链后秒断**
   ```
   P2P连接成功 → 4次握手完成 → NL80211_CMD_DISCONNECT → 断开连接
   ```
   - 关键TAG: 建链后秒断, 断开连接
   - 典型案例: 待补充

6. **EAPOL MIC失败**
   ```
   P2P连接 → 4次握手 → Invalid EAPOL-Key MIC → 认证失败
   ```
   - 关键TAG: EAPOL MIC失败, 4次握手失败
   - 典型案例: 待补充

7. **认证阶段失败**
   ```
   扫描成功 → 认证失败 → 连接失败
   ```
   - 关键TAG: 认证失败, PSK不匹配
   - 典型案例: 待补充

8. **关联拒绝**
   ```
   扫描成功 → 关联请求 → ASSOC-REJECT → 连接失败
   ```
   - 关键TAG: 关联拒绝
   - 典型案例: 待补充

9. **DHCP NAK**
   ```
   P2P连接成功 → DHCP DISCOVER → DHCP OFFER → DHCP NAK → DHCP失败
   ```
   - 关键TAG: DHCP NAK, DHCP失败
   - 典型案例: 待补充

10. **DNS/网络验证失败**
    ```
    WiFi连接成功 → DHCP成功 → DNS超时/网络验证失败 → 无互联网
    ```
    - 关键TAG: DNS超时, DNS解析失败, 网络验证失败, 无互联网
    - 典型案例: 待补充

11. **固件崩溃导致断开**
    ```
    WiFi正常使用 → 固件崩溃(SSR) → 断开连接 → 重连
    ```
    - 关键TAG: 固件崩溃, 断开连接
    - 典型案例: 待补充

12. **Doze模式断开**
    ```
    WiFi连接 → 设备空闲 → Doze模式 → 断开连接
    ```
    - 关键TAG: Doze模式, Doze模式断开
    - 典型案例: 待补充

13. **漫游失败**
    ```
    WiFi连接 → 信号弱 → 漫游尝试 → 漫游失败 → 断开连接
    ```
    - 关键TAG: 信号弱, 漫游失败, 断开连接
    - 典型案例: 待补充

14. **热节流导致性能下降**
    ```
    WiFi正常使用 → 设备过热 → 热节流 → 吞吐量低/延迟高
    ```
    - 关键TAG: 热事件, 热节流, 吞吐量低, 延迟高
    - 典型案例: 待补充

15. **WifiNetworkQuality 触发断连**
    ```
    WiFi连接（强信号） → isHighPingDelay=true → start scan → 扫描失败(status=-9) → tear down wlan0 → network lost
    ```
    - 关键TAG: WifiNetworkQuality断连, isHighPingDelay, wlan0 tear down, WificondScannerImpl失败, network lost
    - 典型案例: CASE-012（背景事件，19:34:04）

16. **应用层网络误报（系统WiFi正常）**
    ```
    WiFi连接+validated（Ping/Probe正常，PER 0~3%） → 第三方App展示网络不可用 → 状态栏WiFi仍连接 → 测速验证网络可用
    ```
    - 关键TAG: 应用层网络误报, SBE abnormal implementation, 截图时刻PER正常
    - 鉴别: 同时段无 network lost / torn down wlan0；kernel PER 截图时刻 ≤10%
    - 典型案例: CASE-012（TOS163-35222，主因）

## 快速匹配规则

### 按日志关键词匹配

| 关键词 | TAG | 问题类型 |
|--------|-----|----------|
| `p2p Conflict` | P2P冲突 | P2P连接失败 |
| `P2P-GROUP-FORMATION-FAILURE` | Group Formation超时 | P2P连接失败 |
| `WIFI_P2P_TIMEOUT` | P2P超时 | P2P连接失败 |
| `GC未加入` | GC超时 | P2P连接失败 |
| `NL80211_CMD_DISCONNECT` | 建链后秒断 | P2P连接失败 |
| `Invalid EAPOL-Key MIC` | EAPOL MIC失败 | 认证失败 |
| `deviceMac not match` | 应用层MAC/握手 | 业务失败 |
| `getApfCapabilities failed: ENOSYS` | APF ENOSYS | DHCP失败 |
| `ILLEGAL ARGUMENT` | DhcpClient ILLEGAL ARGUMENT | DHCP失败 |
| `DHCP: Send REQUEST` (重传) | DHCP REQUEST无ACK | DHCP失败 |
| `Received DHCPNAK` | DHCP NAK | DHCP失败 |
| `CMD_IP_CONFIGURATION_LOST` | IP配置丢失 | 断开连接 |
| `lease expired` | DHCP租约过期 | 断开连接 |
| `interfaceSetCfg` (缺失) | IP地址未配置 | 业务失败 |
| `CTRL-EVENT-DISCONNECTED reason=2` | 认证失败 | 认证失败 |
| `Authentication failure` | 认证失败 | 认证失败 |
| `CTRL-EVENT-ASSOC-REJECT` | 关联拒绝 | 连接失败 |
| `WPA: 4-Way Handshake failed` | 4次握手失败 | 认证失败 |
| `SAE: authentication failure` | WPA3/SAE失败 | 认证失败 |
| `CTRL-EVENT-EAP-FAILURE` | EAP失败 | 认证失败 |
| `Scan failed` | 扫描失败 | 连接失败 |
| `Failed to start PNO scan` | PNO扫描失败 | 连接失败 |
| `Cannot find network` | 未找到网络 | 连接失败 |
| `Roaming failed` | 漫游失败 | 断开连接 |
| `BSSID blacklisted` | BSSID黑名单 | 连接失败 |
| `SSR`, `subsystem restart` | 固件崩溃 | 断开连接 |
| `locally_generated=0 reason=3` | AP发起解认证 | 断开连接 |
| `IpReachabilityMonitor: FAILURE` | 网关不可达 | 断开连接 |
| `DeviceIdle.*IDLE` | Doze模式断开 | 断开连接 |
| `DnsResolver: DNS query timeout` | DNS超时 | 网络不可用 |
| `Captive portal detected` | 强制门户 | 网络受限 |
| `Network has no internet access` | 无互联网 | 网络不可用 |
| `thermal throttling` | 热节流 | 性能问题 |
| `isHighPingDelay : true` | WifiNetworkQuality断连 | 断开连接 |
| `torn down Iface.*wlan0` | wlan0 tear down | 断开连接 |
| `WificondScannerImpl: Failed to start scan` | WificondScannerImpl失败 | 扫描失败 |
| `Wifi network lost` | network lost | 断开连接 |
| `ConnectivityService: Update score for net` | Update score for net | 选网打分/感叹号 |
| `ConnectivityService: Update capabilities for net` | Update capabilities for net | 网络能力/半通/门户 |
| `+TRANSPORT_PRIMARY` | TRANSPORT_PRIMARY主传输通道 | 已当主网候选≠已验证上网 |
| `YIELD_TO_BAD_WIFI` | YIELD_TO_BAD_WIFI对坏WiFi让步 | 坏WiFi时蜂窝救场 |
| `+IS_VALIDATED` / `-IS_VALIDATED` | IS_VALIDATED当前已验证 | 此刻通网 / 感叹号 |
| `+EVER_VALIDATED` | EVER_VALIDATED曾经验证过 | 历史良民证 |
| `-VALIDATED+PARTIAL` ↔ `-PARTIAL+VALIDATED` | 网络波动短暂失验恢复 | 短暂断流自愈 |
| `PARTIAL_CONNECTIVITY` | 部分连通PARTIAL_CONNECTIVITY | 半通 |
| `Update capabilities.*CAPTIVE_PORTAL` | capabilities强制门户CAPTIVE_PORTAL | 门户；须定侧 |
| `networkAddInterface` | networkAddInterface定传输侧 | 确认 netId=WiFi/蜂窝/P2P |
| `SBE.*abnormal implementation` | 应用层网络误报 | 业务失败 |
| `wlanLinkQualityMonitor.*PER\([0-9]\)` | 截图时刻PER正常 | 鉴别应用层误报 |
