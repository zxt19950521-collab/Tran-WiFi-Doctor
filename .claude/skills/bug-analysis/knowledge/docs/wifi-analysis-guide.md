# WiFi 问题分析指南

## 快速开始

### 触发分析

```
# 方式1：直接描述问题
分析这个 WiFi 问题：手机向PC分享图片时提示连接失败

# 方式2：提供日志路径
分析这个日志 D:\logs\wifi-log.txt

# 方式3：提供 Jira 单号
分析 OS162-40436
```

### 分析流程

1. **初步识别**：从描述或日志中识别问题类型
2. **TAG 提取**：自动提取相关 TAG
3. **案例匹配**：优先匹配已有案例
4. **输出结论**：有案例引用案例，无案例独立分析

## 问题类型识别

### P2P 连接问题

**特征关键词**：
- `P2P-GROUP-STARTED`
- `P2P-GROUP-FORMATION-FAILURE`
- `p2p Conflict`
- `WIFI_P2P_TIMEOUT`
- `GC未加入`

**常见场景**：
- 极速互传（手机传文件到PC）
- WiFi Direct 连接
- 投屏连接

### DHCP 问题

**特征关键词**：
- `DHCP timeout`
- `DHCP: Send REQUEST` (重传)
- `getApfCapabilities failed: ENOSYS`
- `ILLEGAL ARGUMENT`
- `interfaceSetCfg` (缺失)

**常见场景**：
- P2P连接成功但业务失败
- IP地址获取失败
- 网络不可用

### 认证问题

**特征关键词**：
- `CTRL-EVENT-DISCONNECTED reason=2`
- `Authentication failure`
- `WPA: 4-Way Handshake failed`

**常见场景**：
- WiFi连接失败
- 密码错误
- 认证超时

### 断开连接问题

**特征关键词**：
- `CTRL-EVENT-DISCONNECTED`
- `RSSI` (低信号)
- `ROAMING-FAILED`

**常见场景**：
- WiFi频繁断开
- 信号弱断开
- 漫游失败

### 连接发起方识别（WifiService: connect）

**特征日志**：
```
WifiService: connect uid=... packageNameToUse=com.android.systemui
WifiService: connect uid=... packageNameToUse=com.android.settings
```

**解读规则**：

| packageNameToUse | 含义 |
|------------------|------|
| `com.android.systemui` | SystemUI/框架代发，常见于自动选网、连通性恢复（**非用户手动点 WiFi 列表**） |
| `com.android.settings` | 用户在 WiFi 设置页手动连接 |
| 其他包名 | 对应第三方应用发起 |

**分析要点**：SSID 切换或 `network lost` 后，查同时间窗 `WifiService: connect` 的 `packageNameToUse`，区分用户操作 vs 框架策略。详见 `tags-knowledge.md`「框架连接日志解读」。

### 网络验证状态（ConnectivityService: Update score / Update capabilities）

**特征日志（管家关键字）**：
```
ConnectivityService: Update capabilities for net 212 : -VALIDATED+PARTIAL_CONNECTIVITY
ConnectivityService: Update score for net 212 : -IS_VALIDATED
ConnectivityService: Update capabilities for net 213 : +VALIDATED
ConnectivityService: Update score for net 213 : +EVER_VALIDATED+IS_VALIDATED
```

**解读规则**：

| 标记 | 含义 |
|------|------|
| capabilities `+VALIDATED` / score `+IS_VALIDATED` | **此刻**可上网 |
| score `+EVER_VALIDATED` | **曾经**验证通过（可与 `-IS_VALIDATED` 并存） |
| capabilities `+PARTIAL_CONNECTIVITY` | **半通** |
| capabilities `+CAPTIVE_PORTAL` | 门户结论（须 `networkAddInterface` 定侧） |
| score `+TRANSPORT_PRIMARY` | **主传输通道/默认网候选**（≠已验证） |
| score `+YIELD_TO_BAD_WIFI` | 对坏 WiFi 让步；多见于蜂窝救场 |
| score `-IS_VALIDATED`，或仅 `+TRANSPORT_PRIMARY` | **感叹号** |
| 仅 `+EVER_EVALUATED` | ≠可上网，且 ≠`EVER_VALIDATED` |

详见 `tags-knowledge.md`「网络验证状态日志解读」。

### netId 传输侧（netd: networkAddInterface）

**特征日志**：
```
netd: networkAddInterface(213, wlan0)
netd: networkAddInterface(214, ccmni0)
```

**解读规则**：`wlan0`=WiFi，`ccmni*`/`rmnet*`=蜂窝，`p2p0`=P2P。分析 `Update score/capabilities for net <id>` 时必须对齐 ifName，详见 `tags-knowledge.md`「netId 传输侧判定」。

## TAG 使用技巧

### 自动提取

系统会自动从日志中提取以下 TAG：

| 日志模式 | 提取的 TAG |
|----------|-----------|
| `p2p Conflict` | P2P冲突 |
| `WIFI_P2P_TIMEOUT` | P2P超时 |
| `getApfCapabilities failed: ENOSYS` | APF ENOSYS |
| `ILLEGAL ARGUMENT` | DhcpClient ILLEGAL ARGUMENT |
| `DHCP: Send REQUEST` (重传) | DHCP REQUEST无ACK |

### 手动补充

如果自动提取不完整，可以手动补充：

```
问题：P2P连接成功但业务失败
TAG：P2P连接成功, 4次握手成功, DHCP失败, IP地址未配置
```

## 案例匹配规则

### 匹配优先级

1. **TAG 完全匹配**：当前 TAG 与案例 TAG 完全一致
2. **TAG 部分匹配**：当前 TAG 与案例 TAG 有交集
3. **关键词匹配**：日志关键词与案例描述匹配
4. **症状匹配**：问题现象与案例症状相似

### 匹配度计算

```
匹配度 = (匹配的 TAG 数量 / 案例 TAG 总数) × 100%
```

- **> 70%**：高度匹配，直接引用案例
- **40-70%**：中度匹配，引用案例但需补充分析
- **< 40%**：低度匹配，进入独立分析

## 独立分析步骤

### 步骤 1：确定问题类型

根据日志关键词判断问题类型：
- P2P连接问题
- DHCP问题
- 认证问题
- 断开连接问题
- 性能问题

### 步骤 2：提取关键事件

从日志中提取关键事件：
- 时间点
- 事件类型
- 成功/失败状态

### 步骤 3：构建时间线

按时间顺序排列关键事件：
```
14:45:37.495 - P2P GC启动
14:45:37.686 - WiFi关联成功
14:45:37.791 - 4次握手完成
14:45:37.816 - IpClient APF ENOSYS错误
14:45:37.830 - DhcpClient ILLEGAL ARGUMENT
14:45:47.539 - 超时失败
```

### 步骤 4：定位根因

根据时间线和 TAG 关联分析，定位根因：
- 失败点在哪里？
- 为什么会失败？
- 根本原因是什么？

### 步骤 5：输出结论

按照标准格式输出结论：
- 问题现象
- TAG 标识
- 根因分析
- 关键日志
- 建议措施

## 常见问题模式

### 模式 1：P2P连接成功后业务失败

```
P2P连接成功 → 4次握手成功 → DHCP失败 → IP地址未配置 → 业务失败
```

**关键检查点**：
- 是否有 `getApfCapabilities failed: ENOSYS`？
- 是否有 `ILLEGAL ARGUMENT`？
- 是否有 `interfaceSetCfg` 日志？

**典型案例**：CASE-003

### 模式 2：P2P连接阶段失败

```
P2P发起 → GC扫描失败 → GC超时 → P2P超时 → 连接失败
```

**关键检查点**：
- GC 是否扫描到 GO？
- 是否有 `GC未加入` 日志？
- 超时时间是多少？

**典型案例**：CASE-002

### 模式 3：P2P冲突导致失败

```
P2P连接 → P2P冲突 → 断开连接 → 连接失败
```

**关键检查点**：
- 是否有 `p2p Conflict`？
- 断开原因是什么？
- 是否有资源冲突？

**典型案例**：CASE-001

## 输出示例

### 示例 1：匹配到案例

```markdown
## 问题分析结论

### 问题现象
手机向PC分享图片时提示连接失败，P2P连接成功但业务无法工作。

### TAG 标识
- P2P连接成功
- 4次握手成功
- DHCP失败
- APF ENOSYS
- IP地址未配置

### 根因分析
P2P接口(p2p0)不支持APF，IpClient获取APF能力时返回ENOSYS错误，导致DhcpClient初始化失败，IP地址无法配置到接口。

### 关键日志
```
05-29 14:45:37.816116 E IpClient.p2p0: ERROR [Non-HAL API] Cannot get APF capabilities: : getApfCapabilities failed: ENOSYS (Function not implemented)
05-29 14:45:37.830293 E DhcpClient: Error retrieving network attributes: ILLEGAL ARGUMENT
```

### 匹配案例
- CASE-003: 手机向PC分享图片/文档提示连接失败（P2P连接成功后DHCP失败）
```

### 示例 2：独立分析

```markdown
## 问题分析结论

### 问题现象
WiFi连接频繁断开，信号强度正常。

### TAG 标识
- 断开连接
- 信号正常

### 根因分析
WiFi连接在认证阶段失败，AP端主动断开连接。可能原因：AP配置问题或认证超时。

### 关键日志
```
05-29 14:45:37.816116 I wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=6a:7a:64:bc:09:67 reason=2
```

### 建议措施
1. 检查AP端认证配置
2. 确认认证方式是否兼容
3. 尝试更换认证方式
```
