# WiFi 问题快速参考卡

## 问题类型速查

| 问题类型 | 关键词 | 典型 TAG | 案例 |
|---------|--------|----------|------|
| P2P连接失败 | `P2P-GROUP-FORMATION-FAILURE`, `p2p Conflict` | P2P冲突, GC超时, P2P超时, Group Formation超时 | CASE-001, CASE-002 |
| P2P建链后秒断 | `NL80211_CMD_DISCONNECT`, `reason=0` | 建链后秒断 | - |
| EAPOL MIC失败 | `Invalid EAPOL-Key MIC` | EAPOL MIC失败, 4次握手失败 | - |
| DHCP失败 | `DHCP timeout`, `ILLEGAL ARGUMENT` | DHCP失败, APF ENOSYS, IP地址未配置 | CASE-003 |
| DHCP NAK | `Received DHCPNAK` | DHCP NAK | - |
| 认证失败 | `Authentication failure`, `reason=2` | 认证失败, PSK不匹配 | - |
| 关联拒绝 | `CTRL-EVENT-ASSOC-REJECT` | 关联拒绝 | - |
| 4次握手失败 | `WPA: 4-Way Handshake failed`, `reason=15` | 4次握手失败 | - |
| EAP失败 | `CTRL-EVENT-EAP-FAILURE` | EAP失败 | - |
| WPA3/SAE失败 | `SAE: authentication failure` | WPA3/SAE失败 | - |
| 扫描失败 | `Scan failed` | 扫描失败, PNO扫描失败 | - |
| 未找到网络 | `Cannot find network` | 未找到网络 | - |
| 漫游失败 | `Roaming failed` | 漫游失败, 过度漫游 | - |
| 断开连接 | `CTRL-EVENT-DISCONNECTED` | 断开连接, 固件崩溃, AP发起解认证 | - |
| DNS/网络问题 | `DNS query timeout`, `Captive portal` | DNS超时, 强制门户, 无互联网 | - |
| 性能问题 | `thermal throttling`, `Tput:` | 热节流, 吞吐量低, RSSI低 | - |

## TAG 速查表

### P2P 连接类
- **P2P冲突** - `p2p Conflict`, `P2P-GROUP-FORMATION-FAILURE`
- **GC超时** - `GC未加入`, `10秒超时`
- **P2P超时** - `WIFI_P2P_TIMEOUT`, `notifyConnectFail`
- **Group Formation超时** - `P2P: Group Formation timed out`
- **建链后秒断** - `NL80211_CMD_DISCONNECT`, `reason=0`
- **EAPOL MIC失败** - `Invalid EAPOL-Key MIC - dropping packet`
- **应用层MAC/握手** - `deviceMac not match`
- **P2P连接成功** - `P2P-GROUP-STARTED`
- **4次握手成功** - `Key negotiation completed`

### DHCP 类
- **DHCP失败** - `DHCP timeout`, `Failed to get DHCP lease`, `No DHCPOFFER received`
- **DHCP超时** - `DHCP REQUEST` 重传
- **DHCP REQUEST无ACK** - `DHCP: Send REQUEST` 重传4次
- **DHCP NAK** - `Received DHCPNAK`
- **DHCP DECLINE** - `Sending DHCPDECLINE`
- **IP配置丢失** - `CMD_IP_CONFIGURATION_LOST`
- **配置失败** - `IpClient: onProvisioningFailure`
- **APF ENOSYS** - `getApfCapabilities failed: ENOSYS`
- **DhcpClient ILLEGAL ARGUMENT** - `ILLEGAL ARGUMENT`
- **IpClient初始化失败** - `IpClient.*ERROR`
- **IP地址未配置** - 无 `interfaceSetCfg`
- **DHCP租约过期** - `lease expired`

### 认证类
- **认证失败** - `CTRL-EVENT-DISCONNECTED reason=2`, `Authentication failure`
- **PSK不匹配** - `PREV_AUTH_NOT_VALID`
- **密钥错误** - `WPA: 4-Way Handshake failed`
- **4次握手失败** - `reason=15`
- **组密钥握手超时** - `reason=16`
- **EAP失败** - `CTRL-EVENT-EAP-FAILURE`, `EAP-TLS: TLS processing failed`
- **WPA3/SAE失败** - `SAE: authentication failure`
- **关联拒绝** - `CTRL-EVENT-ASSOC-REJECT status_code=<N>`
- **关联超时** - `CTRL-EVENT-SSID-TEMP-DISABLED`
- **EAPOL MIC失败** - `Invalid EAPOL-Key MIC`

### 扫描类
- **扫描失败** - `Scan failed`, `getScanResults failed`
- **PNO扫描失败** - `Failed to start PNO scan`
- **扫描节流** - `Scan request throttled`
- **未找到网络** - `connectToNetwork: Cannot find network`, `No candidates selected`

### 断开连接类
- **断开连接** - `CTRL-EVENT-DISCONNECTED`
- **信号弱** - `RSSI` 低
- **漫游失败** - `Roaming failed`
- **过度漫游** - `Multiple BSSID changes detected in short window`
- **BSSID黑名单** - `BSSID blacklisted`
- **固件崩溃** - `SSR`, `subsystem restart`, `firmware crash`
- **AP发起解认证** - `locally_generated=0 reason=3`
- **网关不可达** - `IpReachabilityMonitor: FAILURE`, `Lost default router`
- **Doze模式断开** - `DeviceIdle ... IDLE`
- **不活动解除关联** - `reason=4`
- **DHCP租约过期** - `lease expired`

### DNS/网络验证类
- **DNS超时** - `DnsResolver: DNS query timeout`
- **DNS解析失败** - `NetworkMonitor: DNS resolution failed`
- **网络验证失败** - `HTTPS probe failed`
- **强制门户** - `Captive portal detected`
- **无互联网** - `Network has no internet access`

### 性能类
- **吞吐量低** - `Tput:` 低值
- **延迟高** - `latency` 高
- **丢包** - `PER(` 高值, `packet loss`
- **通道拥塞** - 同信道多BSSID
- **省电模式激进** - 屏幕关闭后延迟飙升
- **热节流** - `thermal throttling`
- **RSSI低** - `mtk_cfg80211_get_station ... rssi=` 低值
- **协商速率低** - `wlanLinkQualityMonitor ... Tx(rate:` 低值

### 系统事件类
- **屏幕状态变化** - `screen on`, `screen off`
- **Doze模式** - `DeviceIdle`, `IDLE`
- **飞行模式** - `airplane mode`
- **热事件** - `thermal`, `temperature`
- **内存压力** - `low memory`, `memory pressure`

## 断开原因代码速查

| 代码 | 含义 | 对应TAG |
|-----:|------|---------|
| 0 | 未指定原因 | 建链后秒断 |
| 2 | 之前的认证不再有效 | PSK不匹配, 认证失败 |
| 3 | 站点离开而解认证 | AP发起解认证 |
| 4 | 不活动而解除关联 | 不活动解除关联 |
| 15 | 4次握手超时 | 4次握手失败 |
| 16 | 组密钥握手超时 | 组密钥握手超时 |

## 分析流程速查

```
1. 识别问题类型
   ↓
2. 提取 TAG
   ↓
3. 匹配案例（优先）
   ↓
4. 有匹配 → 输出案例结论
   无匹配 → 独立分析
   ↓
5. 输出结论
```

## 匹配度判断

- **> 70%**：直接引用案例
- **40-70%**：引用案例 + 补充分析
- **< 40%**：独立分析

## 常见问题模式

### 模式 1：P2P连接成功后业务失败
```
P2P连接成功 → 4次握手成功 → DHCP失败 → IP地址未配置 → 业务失败
```
**检查点**：APF ENOSYS, ILLEGAL ARGUMENT, interfaceSetCfg

### 模式 2：P2P连接阶段失败
```
P2P发起 → GC扫描失败 → GC超时 → P2P超时 → 连接失败
```
**检查点**：GC扫描, GC加入, 超时时间

### 模式 3：Group Formation超时
```
P2P发起 → Group Formation超时 → P2P-GROUP-FORMATION-FAILURE → 连接失败
```
**检查点**：Group Formation timed out, ASSOCIATING状态

### 模式 4：建链后秒断
```
P2P连接成功 → 4次握手完成 → NL80211_CMD_DISCONNECT → 断开连接
```
**检查点**：COMPLETED后立即DISCONNECTED, reason=0

### 模式 5：EAPOL MIC失败
```
P2P连接 → 4次握手 → Invalid EAPOL-Key MIC → 认证失败
```
**检查点**：EAPOL-Key MIC校验失败, PSK可能错误

### 模式 6：P2P冲突导致失败
```
P2P连接 → P2P冲突 → 断开连接 → 连接失败
```
**检查点**：p2p Conflict, 断开原因

### 模式 7：认证失败
```
扫描成功 → 关联请求 → 认证失败 → 连接失败
```
**检查点**：reason=2, auth_failures递增, SSID-TEMP-DISABLED

### 模式 8：关联拒绝
```
扫描成功 → 关联请求 → ASSOC-REJECT → 连接失败
```
**检查点**：status_code=17 (AP关联表已满)

### 模式 9：DNS/网络验证失败
```
WiFi连接成功 → DHCP成功 → DNS超时/网络验证失败 → 无互联网
```
**检查点**：DNS query timeout, HTTPS probe failed, Captive portal

### 模式 10：固件崩溃
```
WiFi正常使用 → 固件崩溃(SSR) → 断开连接 → 重连
```
**检查点**：SSR, subsystem restart, firmware crash

### 模式 11：Doze模式断开
```
WiFi连接 → 设备空闲 → Doze模式 → 断开连接
```
**检查点**：DeviceIdle IDLE后断开

### 模式 12：漫游失败
```
WiFi连接 → 信号弱 → 漫游尝试 → 漫游失败 → 断开连接
```
**检查点**：Roaming failed, RSSI低

### 模式 13：热节流
```
WiFi正常使用 → 设备过热 → 热节流 → 吞吐量低/延迟高
```
**检查点**：thermal throttling, Tput低

## 框架连接日志速查（WifiService: connect）

| 日志 | 含义 |
|------|------|
| `WifiService: connect uid=` | 有一次 WiFi 连接请求 |
| `packageNameToUse=com.android.systemui` | **SystemUI/框架代发**（自动选网、连通性恢复等） |
| `packageNameToUse=com.android.settings` | **用户**在设置里手动连接 |
| `packageNameToUse=<其他>` | 对应应用发起连接 |

分析 SSID 切换 / `network lost` 时，必须与 `WifiService: connect` 时间对齐，避免把框架自动切网误判为用户操作。

## 网络验证状态速查（ConnectivityService）

| 行末 score 标记 | 含义 |
|----------------|------|
| `+EVER_EVALUATED` / `+IS_VALIDATED` | **已验证可上网**，状态栏正常 |
| `-IS_VALIDATED` | **失去验证**，状态栏**感叹号** |
| 仅 `+TRANSPORT_PRIMARY` 等，无 EVER_EVALUATED | 尚未验证完成，**感叹号** |

```
ConnectivityService: Update score for net 183 : -IS_VALIDATED
ConnectivityService: Update score for net 191 : +EVER_VALIDATED+IS_VALIDATED
```

## 输出模板

```markdown
## 问题分析结论

### 问题现象
<现象描述>

### TAG 标识
<TAG 列表>

### 根因分析
<根因描述>

### 关键日志
```
<日志片段>
```

### 建议措施
1. <建议1>
2. <建议2>

### 匹配案例（如有）
- CASE-XXX: <案例标题>
```
