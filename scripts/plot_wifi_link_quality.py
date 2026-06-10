#!/usr/bin/env python3
"""
WiFi Link Quality 绘图脚本
从 MTK kernel log 中提取 Tput/Tx(rate)/Rx(rate)/rssi/PER 数据并绘制四象限曲线图。

数据来源：
- Tput: kalPerMonUpdate 中的吞吐量
- Tx(rate): wlanLinkQualityMonitor 中的发送 PHY Rate
- Rx(rate): wlanLinkQualityMonitor 中的接收 PHY Rate
- rssi: mtk_cfg80211_get_station 中的 rssi 或 MovAvg_rssi
- PER: wlanLinkQualityMonitor 或 mtk_cfg80211_get_station 中的 PER

用法：
  # 命令行
  python scripts/plot_wifi_link_quality.py <kernel_log_file>
  python scripts/plot_wifi_link_quality.py AI-result/issues/XXX/logs/kernel_log.localtime

  # 作为模块导入
  from scripts.plot_wifi_link_quality import plot_from_file
  plot_from_file("path/to/kernel_log.localtime", output_dir="AI-result/issues/XXX/")
"""

import re
import os
import sys
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    print("正在安装 matplotlib...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates


def extract_data(file_path):
    """
    从 kernel log 提取 Tput/Tx/Rx/rssi/PER 数据。
    时间提取：每行前19字符（格式：MM-DD HH:MM:SS.mmm）
    rssi 优先级：, rssi= → MovAvg_rssi=
    """
    data = {
        "Tput:": ([], []),
        "Tx(rate:": ([], []),
        "Rx(rate:": ([], []),
        ", rssi=": ([], []),
        "PER": ([], [])
    }
    all_valid_times = []

    rssi_keywords = [
        (", rssi=", re.compile(r',\s*rssi=(-?\d+\.?\d*)[,)]')),
        ("MovAvg_rssi=", re.compile(r'MovAvg_rssi=(-?\d+\.?\d*)[,)]'))
    ]
    other_pattern_map = {
        "Tput:": re.compile(r'Tput:\s*(\d+\.?\d*)'),
        "Tx(rate:": re.compile(r'Tx\(rate:\s*(\d+\.?\d*)'),
        "Rx(rate:": re.compile(r'Rx\(rate:\s*(\d+\.?\d*)'),
        "PER": re.compile(r'PER\((\d+\.?\d*)\)')
    }

    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    lines = []
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    if not lines:
        print(f"无法解码文件：{file_path}")
        return None, None

    # 提取 Tput/Tx/Rx/PER
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        time_str = line[:19].strip()
        if len(time_str) < 15:
            continue
        try:
            time_obj = datetime.strptime(time_str, '%m-%d %H:%M:%S.%f')
            time_obj = time_obj.replace(year=2026)
        except ValueError:
            continue

        for keyword, pattern in other_pattern_map.items():
            match = pattern.search(line)
            if match:
                try:
                    num = float(match.group(1))
                    data[keyword][0].append(time_obj)
                    data[keyword][1].append(num)
                    if time_obj not in all_valid_times:
                        all_valid_times.append(time_obj)
                except ValueError:
                    continue

    # rssi fallback 提取
    used_keyword = None
    for keyword, pattern in rssi_keywords:
        current_times, current_nums = [], []
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
            time_str = line[:19].strip()
            if len(time_str) < 15:
                continue
            try:
                time_obj = datetime.strptime(time_str, '%m-%d %H:%M:%S.%f')
                time_obj = time_obj.replace(year=2026)
            except ValueError:
                continue
            match = pattern.search(line)
            if match:
                try:
                    num = float(match.group(1))
                    current_times.append(time_obj)
                    current_nums.append(num)
                    if time_obj not in all_valid_times:
                        all_valid_times.append(time_obj)
                except ValueError:
                    continue
        if current_nums:
            data[", rssi="] = (current_times, current_nums)
            used_keyword = keyword
            break

    # 排序
    for keyword in data:
        times, nums = data[keyword]
        if times and nums:
            sorted_pairs = sorted(zip(times, nums), key=lambda x: x[0])
            data[keyword] = ([p[0] for p in sorted_pairs], [p[1] for p in sorted_pairs])

    # 统计
    print("\n数据提取统计：")
    for keyword, (times, nums) in data.items():
        key = "rssi" if keyword == ", rssi=" else keyword
        if nums:
            note = f"（关键字：{used_keyword}）" if keyword == ", rssi=" and used_keyword else ""
            print(f"  {key}：{len(nums)}条 | 范围：{min(nums):.0f}~{max(nums):.0f}{note}")
        else:
            print(f"  {key}：0条有效数据")

    if all_valid_times:
        start = min(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        end = max(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        print(f"时间区间：{start} ~ {end}")

    return data, all_valid_times


def format_x_time(x, pos):
    """将 matplotlib float64 时间戳转回 datetime 并格式化"""
    try:
        time_obj = mdates.num2date(x)
        return time_obj.strftime('%m-%d %H:%M:%S.%f')[:-3]
    except Exception:
        return ""


def plot_quadruple(data, all_valid_times, source_file_path, output_dir=None, save_filename="kernel_log_curves.png"):
    """
    绘制四张子图：Tput → Tx/Rx → rssi → PER
    保存到 source_file_path 同目录或 output_dir 指定目录
    """
    tput_times, tput_nums = data["Tput:"]
    tx_times, tx_nums = data["Tx(rate:"]
    rx_times, rx_nums = data["Rx(rate:"]
    rssi_times, rssi_nums = data[", rssi="]
    per_times, per_nums = data["PER"]

    has_tput = len(tput_times) > 0
    has_tx_rx = len(tx_times) > 0 or len(rx_times) > 0
    has_rssi = len(rssi_times) > 0
    has_per = len(per_times) > 0
    has_time = len(all_valid_times) > 0

    if not has_tput and not has_tx_rx and not has_rssi and not has_per:
        print("无有效数据，跳过绘图")
        return None

    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    plt.rcParams['axes.titlepad'] = 12

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(18, 14), sharex=True)
    plt.subplots_adjust(hspace=0.2, top=0.93, bottom=0.18)

    if has_time:
        start = min(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        end = max(all_valid_times).strftime('%m-%d %H:%M:%S.%f')[:-3]
        fig.suptitle(f'WiFi Link Quality（{start} ~ {end}）', fontsize=16, fontweight='bold', y=0.98)
    else:
        fig.suptitle('WiFi Link Quality', fontsize=16, fontweight='bold', y=0.98)

    # Tput
    if has_tput:
        ax1.plot(tput_times, tput_nums, color='#1f77b4', marker='o', markersize=4, linewidth=1.2, label='Tput')
        ax1.set_ylim(0, max(tput_nums) * 1.1)
        ax1.set_ylabel('Tput (Mbps)', fontsize=12, color='#1f77b4')
        ax1.tick_params(axis='y', labelcolor='#1f77b4')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.legend(loc='upper right', fontsize=10)
        ax1.set_title('Throughput', fontsize=13, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'No Tput data', ha='center', va='center', transform=ax1.transAxes, fontsize=12, color='#666')
        ax1.set_ylabel('Tput (Mbps)', fontsize=12, color='#1f77b4')

    # Tx/Rx
    if has_tx_rx:
        if tx_nums:
            ax2.plot(tx_times, tx_nums, color='#ff7f0e', marker='s', markersize=4, linewidth=1.2, label='Tx(rate)')
        if rx_nums:
            ax2.plot(rx_times, rx_nums, color='#2ca02c', marker='^', markersize=4, linewidth=1.2, label='Rx(rate)')
        max_val = max(max(tx_nums) if tx_nums else 0, max(rx_nums) if rx_nums else 0)
        ax2.set_ylim(0, max_val * 1.1)
        ax2.set_ylabel('PHY Rate (Mbps)', fontsize=12, color='#ff7f0e')
        ax2.tick_params(axis='y', labelcolor='#ff7f0e')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.legend(loc='upper right', fontsize=10)
        ax2.set_title('Tx/Rx PHY Rate', fontsize=13, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'No Tx/Rx data', ha='center', va='center', transform=ax2.transAxes, fontsize=12, color='#666')
        ax2.set_ylabel('PHY Rate (Mbps)', fontsize=12, color='#ff7f0e')

    # rssi
    if has_rssi:
        ax3.plot(rssi_times, rssi_nums, color='#d62728', marker='*', markersize=4, linewidth=1.2, label='RSSI')
        rssi_min, rssi_max = min(rssi_nums), max(rssi_nums)
        y_margin = max(abs(rssi_min) * 0.1, abs(rssi_max) * 0.1, 5)
        ax3.set_ylim(rssi_min - y_margin, rssi_max + y_margin)
        ax3.set_ylabel('RSSI (dBm)', fontsize=12, color='#d62728')
        ax3.tick_params(axis='y', labelcolor='#d62728')
        ax3.grid(True, alpha=0.3, linestyle='--')
        ax3.legend(loc='upper right', fontsize=10)
        ax3.set_title('RSSI', fontsize=13, fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'No RSSI data', ha='center', va='center', transform=ax3.transAxes, fontsize=12, color='#666')
        ax3.set_ylabel('RSSI (dBm)', fontsize=12, color='#d62728')

    # PER
    if has_per:
        ax4.plot(per_times, per_nums, color='#9467bd', marker='d', markersize=4, linewidth=1.2, label='PER')
        per_min, per_max = min(per_nums), max(per_nums)
        y_margin = max(abs(per_min) * 0.1, abs(per_max) * 0.1, 2)
        ax4.set_ylim(per_min - y_margin, per_max + y_margin)
        ax4.set_ylabel('PER', fontsize=12, color='#9467bd')
        ax4.tick_params(axis='y', labelcolor='#9467bd')
        ax4.grid(True, alpha=0.3, linestyle='--')
        ax4.legend(loc='upper right', fontsize=10)
        ax4.set_title('Packet Error Rate', fontsize=13, fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'No PER data', ha='center', va='center', transform=ax4.transAxes, fontsize=12, color='#666')
        ax4.set_ylabel('PER', fontsize=12, color='#9467bd')

    # X 轴
    if has_time:
        ax4.set_xlim(min(all_valid_times), max(all_valid_times))
        tick_count = min(12, max(8, len(all_valid_times) // 80))
        tick_interval = max(1, len(all_valid_times) // tick_count)
        show_times = [all_valid_times[i] for i in range(0, len(all_valid_times), tick_interval)]
        ax4.set_xticks(show_times)
        ax4.xaxis.set_major_formatter(plt.FuncFormatter(format_x_time))
        ax4.tick_params(axis='x', labelrotation=60, width=1.2, length=6)
        plt.draw()
        for label in ax4.get_xticklabels():
            label.set_ha('right')
            label.set_fontweight('bold')
        ax4.set_xlabel('Time (MM-DD HH:MM:SS.mmm)', fontsize=13, fontweight='bold')

    # 保存
    if output_dir:
        save_dir = output_dir
    else:
        save_dir = os.path.dirname(os.path.abspath(source_file_path))
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, save_filename)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n图表已保存到：{save_path}")
    plt.close(fig)
    return save_path


def plot_from_file(file_path, output_dir=None, save_filename="kernel_log_curves.png"):
    """
    一站式接口：提取数据 + 绘图 + 保存
    返回保存路径，失败返回 None
    """
    if not os.path.exists(file_path):
        print(f"文件不存在：{file_path}")
        return None

    data, all_times = extract_data(file_path)
    if data and all_times:
        return plot_quadruple(data, all_times, file_path, output_dir, save_filename)
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <kernel_log_file> [output_dir]")
        print(f"示例: python {sys.argv[0]} AI-result/issues/XXX/logs/kernel_log.localtime")
        sys.exit(1)

    file_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    plot_from_file(file_path, output_dir)
