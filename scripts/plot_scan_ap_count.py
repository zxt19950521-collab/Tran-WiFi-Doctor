#!/usr/bin/env python3
"""
Scan AP 发现数绘图脚本（scnFsmDumpScanDoneInfo）

从 MTK kernel log 的 Scan Done 统计中提取每次扫描发现的 AP 数量并绘制随时间曲线，
用于排查「搜不到 WiFi / 扫描列表为空」类问题。支持 DUT vs REF 对比。

数据来源（scnFsmDumpScanDoneInfo / SCN:500）：
- used[N]              -> 本次扫描发现的 BSS(AP) 数（核心指标，used[0] = 一个都没搜到）
- ucCompleteChanCount -> 本次实际完成扫描的信道数
- Total:X/Y           -> 上报给 kernel 的 AP 数 / 缓存总数（部分平台才有）

用法:
  # 单文件
  python scripts/plot_scan_ap_count.py kernel.localtime

  # DUT vs REF 对比（-l 给每条曲线起名，与文件按顺序对应）
  python scripts/plot_scan_ap_count.py DUT.localtime REF.localtime -l DUT -l REF \
      -o output/ -f TOS163-35374_scan_ap.png

  # 时区对齐：默认按 .localtime 头部 timezone 自动把 UTC 平移到设备本地时间
  #   可用 --no-localtime 关闭，或 --tz-offset N 手动指定
"""

import os
import re
import sys
from datetime import datetime, timedelta

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


# SCN Scan Done 概要：used[N] free[M] ucCompleteChanCount[K]
USED_RE = re.compile(r'used\[(\d+)\]')
CHAN_RE = re.compile(r'ucCompleteChanCount\[(\d+)\]')
# 真正的扫描结果行：Total:报告数/缓存数
TOTAL_RE = re.compile(r'Total:(\d+)/(\d+)')
TS_RE = re.compile(r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)')

PALETTE = ['#d62728', '#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']


def detect_tz_offset_hours(file_path):
    """从 .localtime 头部 'timezone:XXX' 推断 UTC→设备本地 偏移小时数，失败返回 None。"""
    if ZoneInfo is None:
        return None
    tz_name = None
    data_date = None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(30):
                line = f.readline()
                if not line:
                    break
                if tz_name is None:
                    m = re.search(r'timezone:\s*([\w/+\-]+)', line)
                    if m:
                        tz_name = m.group(1).strip()
                if data_date is None:
                    dm = re.match(r'(\d{2})-(\d{2})\s', line)
                    if dm:
                        data_date = (int(dm.group(1)), int(dm.group(2)))
                if tz_name and data_date:
                    break
    except OSError:
        return None
    if not tz_name:
        return None
    try:
        mm, dd = data_date if data_date else (1, 1)
        off = datetime(2026, mm, dd, tzinfo=ZoneInfo(tz_name)).utcoffset()
        return off.total_seconds() / 3600.0 if off is not None else None
    except Exception:
        return None


def parse_ts(line):
    m = TS_RE.match(line)
    if not m:
        return None
    for fmt in ('%m-%d %H:%M:%S.%f', '%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(m.group(1).strip(), fmt).replace(year=2026)
        except ValueError:
            continue
    return None


def extract_scan_counts(file_path, tz_offset_hours=0.0):
    """提取每次 Scan Done 的 (时间, 发现AP数, 完成信道数) 与 Total 结果。

    返回 (times, used_counts, chan_counts, total_times, total_reported)。
    时间统一平移 tz_offset_hours 小时（对齐到设备本地时间）。
    """
    times, used_counts, chan_counts = [], [], []
    total_times, total_reported = [], []
    delta = timedelta(hours=tz_offset_hours or 0.0)

    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    if not lines:
        print(f"无法解码文件：{file_path}")
        return times, used_counts, chan_counts, total_times, total_reported

    for line in lines:
        um = USED_RE.search(line)
        if um and 'ScanDone' in line:
            ts = parse_ts(line)
            if ts is None:
                continue
            cm = CHAN_RE.search(line)
            times.append(ts + delta)
            used_counts.append(int(um.group(1)))
            chan_counts.append(int(cm.group(1)) if cm else 0)
            continue
        tm = TOTAL_RE.search(line)
        if tm:
            ts = parse_ts(line)
            if ts is None:
                continue
            total_times.append(ts + delta)
            total_reported.append(int(tm.group(1)))

    return times, used_counts, chan_counts, total_times, total_reported


def plot_scan_counts(series, output_dir, save_filename):
    """series: list of dict(label, times, used, chans, total_times, total). 绘制对比图。"""
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
    plt.subplots_adjust(hspace=0.18, top=0.93, bottom=0.12)

    any_data = False
    for i, s in enumerate(series):
        color = PALETTE[i % len(PALETTE)]
        if s['times']:
            any_data = True
            ax1.plot(s['times'], s['used'], color=color, marker='o', markersize=5,
                     linewidth=1.6, label=f"{s['label']} 发现AP数 (used[N])")
            # used[0] 红圈强调：一个 AP 都没搜到
            zero_t = [t for t, u in zip(s['times'], s['used']) if u == 0]
            if zero_t:
                ax1.scatter(zero_t, [0] * len(zero_t), s=90, facecolors='none',
                            edgecolors=color, linewidths=1.8, zorder=5)
            ax2.plot(s['times'], s['chans'], color=color, marker='s', markersize=4,
                     linewidth=1.4, label=f"{s['label']} 完成信道数")

    if not any_data:
        print("无 Scan Done 数据，跳过绘图")
        plt.close(fig)
        return None

    ax1.set_ylabel('发现 AP 数 (used[N])', fontsize=12)
    ax1.set_title('Scan 发现 AP 数（used[0] = 一个都没搜到，已用空心圈标注）',
                  fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.set_ylim(bottom=-1)

    ax2.set_ylabel('完成扫描信道数', fontsize=12)
    ax2.set_title('每次 Scan 完成的信道数（信道数正常但 AP=0 → 接收链路异常）',
                  fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(loc='upper left', fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax2.set_xlabel('时间 (HH:MM:SS, 设备本地时间)', fontsize=12, fontweight='bold')
    for lbl in ax2.get_xticklabels():
        lbl.set_rotation(45)
        lbl.set_ha('right')

    fig.suptitle('WiFi Scan 发现能力对比 (scnFsmDumpScanDoneInfo)',
                 fontsize=15, fontweight='bold', y=0.985)

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, save_filename)
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    print(f"\n图表已保存到：{save_path}")
    plt.close(fig)
    return save_path


def main():
    args = sys.argv[1:]
    if not args:
        print(f"用法: python {sys.argv[0]} <file1.localtime> [file2 ...] "
              f"[-l LABEL ...] [--tz-offset H] [--no-localtime] [-o out_dir] [-f name.png]")
        sys.exit(1)

    files, labels = [], []
    output_dir = None
    save_filename = "scan_ap_count.png"
    tz_offset_hours = None
    use_localtime = True
    i = 0
    while i < len(args):
        a = args[i]
        if a == '-o' and i + 1 < len(args):
            output_dir = args[i + 1]; i += 2
        elif a == '-f' and i + 1 < len(args):
            save_filename = args[i + 1]; i += 2
        elif a in ('-l', '--label') and i + 1 < len(args):
            labels.append(args[i + 1]); i += 2
        elif a == '--tz-offset' and i + 1 < len(args):
            tz_offset_hours = float(args[i + 1]); i += 2
        elif a == '--no-localtime':
            use_localtime = False; i += 1
        else:
            files.append(a); i += 1

    if not files:
        print("错误：未指定 kernel log 文件")
        sys.exit(1)

    series = []
    for idx, fp in enumerate(files):
        if not os.path.exists(fp):
            print(f"文件不存在，跳过：{fp}")
            continue
        if tz_offset_hours is not None:
            off = tz_offset_hours
        elif use_localtime:
            off = detect_tz_offset_hours(fp)
            off = off if off is not None else 0.0
        else:
            off = 0.0
        label = labels[idx] if idx < len(labels) else os.path.basename(fp)
        t, used, chans, tt, tr = extract_scan_counts(fp, off)
        n_zero = sum(1 for u in used if u == 0)
        print(f"{label}: Scan Done {len(used)} 次 | used=0 占 {n_zero} 次 | "
              f"发现AP范围 {min(used) if used else '-'}~{max(used) if used else '-'} "
              f"| 时区偏移 +{off:.1f}h")
        series.append({'label': label, 'times': t, 'used': used, 'chans': chans,
                       'total_times': tt, 'total': tr})

    out_dir = output_dir or os.path.dirname(os.path.abspath(files[0]))
    plot_scan_counts(series, out_dir, save_filename)


if __name__ == "__main__":
    main()
