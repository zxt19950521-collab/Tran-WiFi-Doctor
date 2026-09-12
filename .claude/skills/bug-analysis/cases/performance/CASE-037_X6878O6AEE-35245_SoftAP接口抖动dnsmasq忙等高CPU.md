# CASE-037: SoftAP/多下游 tethering 接口抖动后 dnsmasq 忙等导致后台 CPU 95%

## 基本信息
- **案例ID**: CASE-037
- **分类**: performance
- **来源**: X6878O6AEE-35245（主单）；重复/同因：X6885O6AEE-40569
- **创建时间**: 2026-09-12
- **匹配次数**: 0

## 现象描述
- HealthCpu 行管 TNE `0x00501007`：进程 `dnsmasq`，ADJ=-1000，CPU Usage ≈93%~95%
- 身份为 Android tethering 组件：`uid=1052`、`user dns_tether`、cmdline 含 `--listen-mark`
- 非三方 App；热点/USB 共享开启或接口抖动后后台单核接近打满

## 根因结论
**Android 自带 dnsmasq 2.51 老问题：下游接口抖动后，DNS listen socket 进入 POLLERR/POLLHUP 却未被主循环摘除，`poll()` 立即返回导致单核 100% 空转。**

不是从设备疯狂解析域名，而是坏 FD 未清理。

### 因果链
```
已有/新建 SoftAP 或 USB/BT 共享
    ↓
下游接口 tearDown / link-local 瞬断 / rndis 重建
    ↓
dnsmasq 为该接口 bind 的 DNS listen fd 变坏（ERR/HUP）
    ↓
2.51 主循环不摘除坏 fd → poll 忙等
    ↓
stime≫utime、低 I/O、单核 93%~100% → HealthCpu TNE
```

### 两单触发差异（同根因）
| 单号 | 平台 | 触发 |
|------|------|------|
| X6878O6AEE-35245 | QCOM SM7635 | SoftAP `wlan1` tearDown 后重建；高 CPU 早于 BT tether |
| X6885O6AEE-40569 | MTK MT6789 | 已有 WiFi tether 后 USB `rndis` uninit→重建，约 10s 内 CPU 飙升 |

## 排查步骤
1. 确认 `cmdline` 含 `dns_tether` / `--listen-mark`，父进程为 netd
2. 看 `tran_health_sched` / top：是否长期 `State: R`、usage≥90%
3. 核对忙等指纹：`stime≫utime`、`syscr/rchar` 很低、voluntary 切换少
4. 时间线对齐 SoftAP tearDown/`START AP`、USB rndis、BT `bt-pan` 等接口事件
5. 复现时对 dnsmasq 抓 `debuggerd`/`simpleperf`，确认卡在 poll 与坏 socket

## 关键日志
```
// HealthCpu
[tran_health_sched] TNE(0x00501007) report comm: dnsmasq ... cpu_usage: 95%
scene_log: dnsmasq=95

// 身份
/system/bin/dnsmasq --keep-in-foreground --no-resolv --no-poll
  --dhcp-authoritative --dhcp-option-force=43,ANDROID_METERED
  --pid-file --listen-mark 0xf0063 --user dns_tether

// 忙等指纹（35245）
utime=853 stime=7017  voluntary=21 involuntary=8457  syscr=96

// SoftAP 抖动（35245）
wificond: tearDownApInterface ... wlan1
wcn6450: wlan1 START AP: mode SAP(1) 2437

// USB rndis 抖动（40569）
mtk_rndis_uninit → sys.usb.config=rndis → rndis0
MdnsSocketProvider: Interface not found: rndis0
Tethering: USB bcast ... rndis:true
约 10s 后 [K] 83%→100% dnsmasq → TNE 93%
```

## TAG
- HealthCpu
- dnsmasq
- dns_tether
- SoftAP
- Tethering
- poll忙等
- POLLERR
- USB-rndis
- 接口抖动
- 后台CPU异常
- X6878
- X6885
- QCOM
- MTK平台

## 相关案例
- CASE-010（同属 SoftAP/tethering 场景，根因不同：热点温升/modem）
- X6885O6AEE-40569（同根因，USB rndis 触发）
