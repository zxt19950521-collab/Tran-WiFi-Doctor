# CASE-044: 快速关开 WiFi 时 wlan0 未创建即下发 resetTxPowerScenario，高通 libwifi-hal 空句柄解引用导致 wifi-service 崩溃

## 基本信息
- **案例ID**: CASE-044
- **分类**: stability
- **来源**: TOS170AEE-24991
- **创建时间**: 2026-10-16
- **匹配次数**: 0

## 现象描述
- FANS 自动上报 DaemonCrash `0x007a0054`（Critical，Total Number 1），无用户描述
- 机型 X6878，版本 X6878-17.0.0.036SP02(OP002PF001AZ)FANS，Android 17，AIDL WiFi HAL
- 高通平台，WLAN FW `WLAN.EVR.1.0-01574-QCAEVRSWPLZ-1.134398.76`
- 崩溃进程 `/vendor/bin/hw/android.hardware.wifi-service`，`signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0 (read)`，`Cause: null pointer dereference`
- 崩溃栈：`libwifi-hal.so wifi_reset_tx_power_scenario.cfi+28` ← `WifiChip::resetTxPowerScenarioInternal()+116` ← `IWifiChip onTransact`（binder 线程）

## 根因结论

**高通 `libwifi-hal.so` 的 `wifi_reset_tx_power_scenario()` 未对接口句柄判空；AOSP WiFi HAL 在无活动 wlan 接口时仍向 vendor 下发空句柄。用户 1 s 内快速关开 WiFi 只是触发条件。**

机理链条：
1. **12:29:08.54** `Wifi turning off`
2. **12:29:09.43** `Wifi Turning On`（与关闭间隔不到 1 s）
3. **12:29:09.443** `Wifi HAL started`，芯片模式和 STA 接口尚未配置
4. **12:29:09.461** `No active wlan interfaces` / `Unknown iface name: wlan0`
   - AOSP `getFirstActiveWlanIfaceName()` 在 `sta_ifaces_`、`ap_ifaces_` 都为空时回退默认名 `wlan0`
   - `WifiLegacyHal::getIfaceHandle("wlan0")` 查不到句柄，返回 nullptr
5. **约 +6 ms** 框架（推断为 `SarManager`，SAR overlay 开启时才会下发）调用 `IWifiChip.resetTxPowerScenario()`，nullptr 句柄传入 `wifi_reset_tx_power_scenario()`，入口 +28 字节处读 0x0 → SIGSEGV
6. wifi-service 被 init 重启，框架感知 HAL 死亡并恢复，本次开 WiFi 失败或变慢

## 排查步骤

1. **tombstone 定位**：`#00` 为 vendor `libwifi-hal.so` 的 `wifi_*_tx_power_scenario`，`#01` 为 `WifiChip::*TxPowerScenarioInternal`，fault addr 0x0 → 句柄为空
2. **确认接口不存在窗口期**：main log 在崩溃前几 ms 搜 `No active wlan interfaces`、`Unknown iface name: wlan0`
3. **确认触发操作**：往前搜 `Wifi turning off` / `Wifi Turning On` / `Wifi HAL started`，确认快速关开（< 1 s）
4. **确认触发源**：搜 `WifiService: setWifiEnabled` 的 package，区分用户（settings）与系统组件（SystemUI / TranSystemUI，参考 CASE-024）
5. **确认调用方**：搜 `SarManager`、`WifiVendorHal`、`selectTxPowerScenario`，并确认 overlay `config_wifi_framework_enable_sar_tx_power_limit=true`
6. **日志留存**：FANS `.tne` 在 NAS 上清理很快（本单上报后 4 天即 `STATUS_NOT_FOUND`），首次解密后应把 tombstone 和 main log 附到 Jira

## 关键日志

```
// main log（负责人摘录）
12:29:08.54  Wifi turning off
12:29:09.43  Wifi Turning On
12:29:09.443 Wifi HAL started
12:29:09.461 No active wlan interfaces ... / Unknown iface name: wlan0

// tombstone
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0000000000000000 (read)
Cause: null pointer dereference
#00 pc 000000000006be34  /vendor/lib64/libwifi-hal.so (wifi_reset_tx_power_scenario.cfi+28) (BuildId: 3e6fdbf734623a80f7cc0fd359376d61)
#01 pc 00000000000296b0  /vendor/bin/hw/android.hardware.wifi-service (aidl::android::hardware::wifi::WifiChip::resetTxPowerScenarioInternal()+116) (BuildId: 1f151a2bfb97a0c3c9cba97d52db9115)
#02 pc 00000000000295e4  /vendor/bin/hw/android.hardware.wifi-service (aidl::android::hardware::wifi::WifiChip::resetTxPowerScenario()+72)
#03 pc 00000000000438f8  /vendor/lib64/android.hardware.wifi-V1-ndk.so (..._IWifiChip_onTransact(...)+4160)
```

## TAG
- DaemonCrash
- WiFi HAL崩溃
- SIGSEGV
- 空指针
- wifi_reset_tx_power_scenario
- resetTxPowerScenario
- SAR/TxPower
- SarManager
- 快速开关WiFi
- iface未创建
- Unknown iface name
- 高通平台
- X6878

## 建议措施

### 高通 vendor HAL（必须）
1. `wifi_reset_tx_power_scenario`、`wifi_select_tx_power_scenario` 及同类以 `wifi_interface_handle` 为入参的接口入口判空，`handle == nullptr` 时返回 `WIFI_ERROR_INVALID_ARGS`
2. 向高通提 Case（附 BuildId `3e6fdbf734623a80f7cc0fd359376d61`、`wifi_reset_tx_power_scenario.cfi+28`），确认是否已有官方 patch

### AOSP WiFi HAL（建议）
3. `WifiChip::resetTxPowerScenarioInternal()` / `selectTxPowerScenarioInternal()` 在无活动 STA/AP 接口时直接返回 `ERROR_NOT_AVAILABLE`；或 `WifiLegacyHal::resetTxPowerScenario()` 对 `getIfaceHandle()` 结果判空，不再调用 vendor 函数表

### 复现
4. 同版本开启 SAR，循环 `cmd wifi set-wifi-enabled disabled` → 间隔 200~800 ms → `enabled`，200 次以上，抓 main log 过滤 `SarManager|WifiVendorHal|WifiChip|android.hardware.wifi`，观察是否出现同栈 tombstone

## 关联案例
- **CASE-043**（同类模式）：上层在对象已不存在时下发操作，下层查表得 NULL 未判空直接解引用；CASE-043 为 MTK 内核驱动 KE，本案为高通用户态 HAL 进程崩溃
- **CASE-024**（待排除）：系统组件异常 toggle WiFi；若本案快速关开并非用户操作，需回看

## 分析报告
- `AI-result/issues/TOS170AEE-24991/TOS170AEE-24991-analysis.md`
- 原始日志：NAS `.tne` 已清理，未能下载；崩溃栈与时序来自 Jira 评论摘录
