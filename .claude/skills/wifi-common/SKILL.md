---
name: wifi-common
description: >-
  WiFi 问题快速分析技能。遇到 WiFi 问题时，先初步分析，优先匹配案例仓库，
  如果没有匹配案例则根据 TAG 知识库进行独立分析并输出结论。
---

# WiFi 问题快速分析

## 触发方式

```
用户：分析这个 WiFi 问题 <描述或日志>
用户：P2P连接失败了
用户：DHCP获取不到IP
用户：WiFi断开连接
```

## 执行流程

### 步骤 1：问题识别与初步分析

1. **识别问题类型**
   - 从用户描述或日志中提取关键信息
   - 识别问题类别：P2P连接、DHCP、认证、扫描、断开、性能

2. **提取 TAG**
   - 根据 `tags-knowledge.md` 中的提取规则
   - 从日志中自动识别 TAG
   - 记录发现的 TAG 列表

### 步骤 2：案例匹配（优先）

1. **读取案例索引**
   ```
   读取 .claude/skills/bug-analysis/cases/index.json
   ```

2. **执行匹配**
   - **TAG 匹配**：当前问题 TAG 与案例 TAG 的交集
   - **关键词匹配**：日志关键词与案例描述的匹配
   - **症状匹配**：问题现象与案例症状的相似度

3. **匹配结果处理**
   - 如果匹配度 > 70%：直接引用案例，输出结论
   - 如果匹配度 40-70%：引用案例，但需要补充分析
   - 如果匹配度 < 40%：进入独立分析

### 步骤 3：独立分析（无匹配案例时）

1. **日志分析**
   - 按问题类型选择分析策略
   - 提取关键事件和时间线
   - 识别失败点

2. **TAG 关联分析**
   - 根据 `tags-knowledge.md` 中的关联分析规则
   - 构建问题链条
   - 定位根因

3. **输出结论**
   - 问题现象
   - 根因分析
   - 关键日志
   - 建议措施

## 分析策略

### P2P 连接问题分析

```
1. 检查 P2P 发起日志
   - 是否有 P2P-GROUP-STARTED？
   - 是否有 Key negotiation completed？

2. 检查 GC 加入情况
   - GC 是否扫描到 GO？
   - GC 是否成功加入？

3. 检查冲突情况
   - 是否有 p2p Conflict？
   - 是否有 CTRL-EVENT-DISCONNECTED？

4. 检查超时情况
   - 是否有 WIFI_P2P_TIMEOUT？
   - 超时时间点在哪里？

5. 检查 Group Formation
   - 是否有 P2P: Group Formation timed out？
   - 是否有 P2P-GROUP-FORMATION-FAILURE？
   - 停留在 ASSOCIATING 状态？

6. 检查建链后秒断
   - 是否有 NL80211_CMD_DISCONNECT？
   - 是否有 CTRL-EVENT-DISCONNECTED reason=0？
   - COMPLETED 后是否立即 DISCONNECTED？

7. 检查 EAPOL MIC
   - 是否有 Invalid EAPOL-Key MIC - dropping packet？
   - 4次握手各阶段是否完成？
   - PSK 是否正确？
```

### DHCP 问题分析

```
1. 检查 Kernel 层 DHCP
   - DHCP DISCOVER 是否发送？
   - DHCP OFFER 是否收到？
   - DHCP REQUEST 是否发送？
   - DHCP ACK 是否收到？

2. 检查 Android 框架层
   - IpClient 是否初始化成功？
   - DhcpClient 是否报错？
   - interfaceSetCfg 是否调用？

3. 检查 IP 配置
   - IP 地址是否分配？
   - IP 地址是否配置到接口？
   - 路由是否添加？

4. 检查 DHCP NAK/DECLINE
   - 是否有 Received DHCPNAK？
   - 是否有 Sending DHCPDECLINE？
   - DHCP 服务器是否正常？

5. 检查 IP 配置丢失
   - 是否有 CMD_IP_CONFIGURATION_LOST？
   - 是否有 onProvisioningFailure？
   - 是否有 lease expired？
```

### 认证问题分析

```
1. 检查扫描结果
   - AP 是否被发现？
   - 信号强度是否足够？

2. 检查认证过程
   - 是否有 Authentication failure？
   - 是否有密钥错误？

3. 检查断开原因
   - reason code 是什么？
   - 是主动断开还是被动断开？

4. 检查 PSK 不匹配
   - 是否有 PREV_AUTH_NOT_VALID？
   - auth_failures 是否递增？
   - 是否有 SSID-TEMP-DISABLED？

5. 检查 EAP 失败
   - 是否有 CTRL-EVENT-EAP-FAILURE？
   - 是否有 EAP-TLS: TLS processing failed？
   - 证书/CA/身份是否正确？

6. 检查 WPA3/SAE
   - 是否有 SAE: authentication failure？
   - 是否需要降级 WPA2？

7. 检查关联拒绝
   - 是否有 CTRL-EVENT-ASSOC-REJECT？
   - status_code 是什么？
   - AP 关联表是否已满（status_code=17）？

8. 检查 4 次握手
   - RX message 1 of 4-Way 是否收到？
   - EAPOL-Key 2/4 是否发送？
   - RX message 3 of 4-Way 是否收到？
   - EAPOL-Key 4/4 是否发送？
   - 是否有 Invalid EAPOL-Key MIC？
```

### DNS/网络验证问题分析

```
1. 检查 DNS
   - 是否有 DNS query timeout？
   - 是否有 DNS resolution failed？
   - DNS 服务器是否可达？

2. 检查网络验证
   - 是否有 HTTPS probe failed？
   - 是否有 Captive portal detected？
   - 是否有 Network has no internet access？

3. 检查网络连通性
   - 网关是否可达？
   - 是否有 Lost default router？
   - 是否有 IpReachabilityMonitor: FAILURE？
```

### 断开连接问题分析

```
1. 检查断开原因
   - reason code 是什么？
   - 是主动断开还是被动断开？

2. 检查固件崩溃
   - 是否有 SSR？
   - 是否有 subsystem restart？
   - 是否有 firmware crash？

3. 检查 AP 发起解认证
   - 是否有 locally_generated=0 reason=3？
   - AP 负载/空闲超时？

4. 检查 DHCP 租约
   - 是否有 lease expired？
   - 是否有 IP_CONFIGURATION_LOST？

5. 检查网关可达性
   - 是否有 IpReachabilityMonitor: FAILURE？
   - 是否有 Lost default router？

6. 检查 Doze 模式
   - 是否有 DeviceIdle IDLE？
   - 断开是否发生在 Doze 后？

7. 检查漫游
   - 是否有 Roaming failed？
   - 是否有 Multiple BSSID changes？
   - 是否有 BSSID blacklisted？
```

### 性能问题分析

```
1. 检查 RSSI
   - mtk_cfg80211_get_station 的 rssi 值？
   - 信号强度是否足够？

2. 检查协商速率
   - wlanLinkQualityMonitor 的 Tx/Rx rate？
   - 协商速率是否正常？

3. 检查吞吐量
   - kalPerMonUpdate 的 Tput 值？
   - 吞吐量是否达到预期？

4. 检查 PER
   - PER 值是否过高？
   - 丢包率是否正常？

5. 检查热节流
   - 是否有 thermal throttling？
   - 设备是否过热？

6. 检查省电模式
   - 屏幕关闭后是否延迟飙升？
   - 省电策略是否过于激进？

7. 检查通道拥塞
   - 同信道是否有多个 BSSID？
   - 是否需要调整信道/带宽？
```

## 输出格式

### 标准输出格式

```markdown
## 问题分析结论

### 问题现象
<简要描述问题现象>

### TAG 标识
<TAG 列表>

### 根因分析
<根因描述>

### 关键日志
```
<关键日志片段>
```

### 建议措施
1. <建议1>
2. <建议2>

### 匹配案例（如有）
- CASE-XXX: <案例标题>
```

## TAG 知识库

详见 `tags-knowledge.md`

## 案例库

案例位于 `.claude/skills/bug-analysis/cases/`

### 案例分类
- p2p-connection：P2P连接失败
- dhcp-failure：DHCP失败
- auth-failure：认证失败
- scan-failure：扫描失败
- disconnect：断开连接
- performance：性能问题

## 硬规则

1. **优先匹配案例库**：有匹配案例时直接引用，不重复分析
2. **TAG 提取必须准确**：基于日志实际内容，不猜测
3. **结论必须有依据**：所有结论必须有日志支持
4. **输出使用中文**：所有分析报告使用中文
