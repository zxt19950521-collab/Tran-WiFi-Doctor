#!/usr/bin/env python3
"""Extract WiFi metrics from CN6OS16-2328 Zoom scenario logs."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from statistics import mean

ISSUE_DIR = Path(r"d:\04_AI\Claude-Wifi-doctor\AI-result\issues\CN6OS16-2328")
LOGS_ROOT = ISSUE_DIR / "logs" / "CN6 PIR" / "CN6"
OUT_PATH = ISSUE_DIR / "zoom_metrics_summary.txt"

ZOOM_Aplog = LOGS_ROOT / "25 zoom" / "debuglogger" / "mobilelog" / "APLog_2026_0703_160559__10"
KERNEL_FILES = [
    ZOOM_Aplog / "kernel_log_8__2026_0703_162553.localtime",
    ZOOM_Aplog / "kernel_log_19__2026_0703_163707.localtime",
]
MAIN_LOG = ZOOM_Aplog / "main_log_14__2026_0703_163707"

RE_TPUT = re.compile(r"kalPerMonUpdate.*?Tput:\s*(\d+)\(([\d.]+)mbps\)")
RE_LQ = re.compile(
    r"wlanLinkQualityMonitor.*?Link Quality: Tx\(rate:(\d+), total:(\d+).*?Rx\(rate:(\d+), total:(\d+)"
)
RE_CONSYS = re.compile(
    r"\[consys_power_state\]\[round:(\d+)\].*?wf:([\d.]+),(\d+);bt:.*?\[total\].*?wf:([\d.]+),(\d+)"
)
RE_TS = re.compile(r"^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")
RE_SETSUSPEND = re.compile(r"SETSUSPENDMODE\s+(\d+)")


def iter_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def parse_tput_file(path: Path) -> tuple[int, int, list[float]]:
    kal_total = nz = 0
    mbps: list[float] = []
    if not path.exists():
        return kal_total, nz, mbps
    for line in iter_lines(path):
        if "kalPerMonUpdate" not in line:
            continue
        m = RE_TPUT.search(line)
        if not m:
            continue
        kal_total += 1
        if int(m.group(1)) > 0:
            nz += 1
            mbps.append(float(m.group(2)))
    return kal_total, nz, mbps


def find_zoom_charging_kernels() -> list[Path]:
    out: list[Path] = []
    for d in LOGS_ROOT.iterdir():
        if d.is_dir() and "zoom" in d.name.lower() and d.name != "25 zoom":
            out.extend(sorted(d.rglob("kernel*.localtime")))
    return out


def format_tput_stats(kal_total: int, nz: int, mbps: list[float]) -> list[str]:
    out = [
        f"  kalPerMonUpdate lines (parsed Tput): {kal_total}",
        f"  Tput > 0 samples: {nz}",
    ]
    if mbps:
        out.append(
            f"  Tput (mbps) min/avg/max: {min(mbps):.3f} / {mean(mbps):.3f} / {max(mbps):.3f}"
        )
    else:
        out.append("  Tput (mbps): no non-zero samples")
    return out


def round_wf_note(on_val: float, aux: int) -> str:
    if on_val <= 1.0:
        return f"round wf duty~{on_val * 100:.1f}%"
    return f"round wf on={on_val}s (aux={aux})"


def assess_wf_sleep(consys_parsed: list[tuple]) -> str:
    """consys entries: (ts, round_n, rwf, rwf_aux, twf_on, twf_off)."""
    if not consys_parsed:
        return "no data"
    reasons: list[str] = []
    last = consys_parsed[-1]
    twf_on, twf_off = last[4], last[5]
    denom = twf_on + twf_off
    if denom:
        off_pct = twf_off / denom * 100
        if off_pct >= 75:
            reasons.append(f"cumulative wf off/(on+off)={off_pct:.1f}% (elevated)")

    duty_samples = [e[2] for e in consys_parsed if e[2] <= 1.0]
    if duty_samples:
        low = sum(1 for d in duty_samples if d < 0.10)
        if low >= max(3, len(duty_samples) // 4):
            reasons.append(
                f"{low}/{len(duty_samples)} round windows with wf duty <10% (possible sleep)"
            )
        if last[2] <= 1.0 and last[2] < 0.10:
            reasons.append(f"last round wf duty {last[2]*100:.1f}% <10%")

    if reasons:
        return "CONCERN - " + "; ".join(reasons)
    return "not obviously bad (cumulative off ~78% is typical for this dump format; no extreme low-duty streak)"


def parse_kernels(paths: list[Path], label: str, lines_out: list[str]) -> None:
    lines_out.append(f"=== Kernel WiFi metrics: {label} ===")
    for p in paths:
        lines_out.append(f"  File: {p.name}" + (" (missing)" if not p.exists() else ""))

    # Per-file Tput
    for p in paths:
        if not p.exists():
            continue
        kal, nz, mbps = parse_tput_file(p)
        extra = ""
        if mbps:
            extra = f"; min/avg/max={min(mbps):.3f}/{mean(mbps):.3f}/{max(mbps):.3f} mbps"
        lines_out.append(f"  [{p.name}] Tput>0: {nz} (of {kal} kalPerMonUpdate){extra}")

    all_mbps: list[float] = []
    nz_count = 0
    kal_total = 0
    lq_count = 0
    lq_samples: list[str] = []
    consys_parsed: list[tuple] = []

    for path in paths:
        if not path.exists():
            continue
        for line in iter_lines(path):
            if "kalPerMonUpdate" in line:
                m = RE_TPUT.search(line)
                if m:
                    kal_total += 1
                    if int(m.group(1)) > 0:
                        nz_count += 1
                        all_mbps.append(float(m.group(2)))
            if "wlanLinkQualityMonitor" in line and "Link Quality:" in line:
                lq_count += 1
                if len(lq_samples) < 5:
                    lq_samples.append(line.strip()[:280])
            if "consys_power_state" in line and "[total]" in line:
                m = RE_CONSYS.search(line)
                if m:
                    ts = line[:18] if len(line) >= 18 else ""
                    consys_parsed.append(
                        (
                            ts,
                            int(m.group(1)),
                            float(m.group(2)),
                            int(m.group(3)),
                            float(m.group(4)),
                            int(m.group(5)),
                        )
                    )

    lines_out.extend(format_tput_stats(kal_total, nz_count, all_mbps))
    lines_out.append(f"  wlanLinkQualityMonitor Link Quality lines: {lq_count}")
    for i, s in enumerate(lq_samples, 1):
        m = RE_LQ.search(s)
        extra = ""
        if m:
            extra = (
                f"  -> Tx rate={m.group(1)} total={m.group(2)}; "
                f"Rx rate={m.group(3)} total={m.group(4)}"
            )
        lines_out.append(f"    sample {i}: {s[:200]}{extra}")

    lines_out.append(f"  consys_power_state [total] wf dumps: {len(consys_parsed)}")
    if consys_parsed:
        for tag, idx in zip(["first", "middle", "last"], [0, len(consys_parsed) // 2, -1]):
            ts, rnd, rwf, rwf_aux, twf_on, twf_off = consys_parsed[idx]
            denom = twf_on + twf_off
            off_pct = (twf_off / denom * 100) if denom else 0
            lines_out.append(
                f"    {tag} [{ts}] round={rnd}: [total] wf:{twf_on},{twf_off} "
                f"(off/(on+off)={off_pct:.1f}%); {round_wf_note(rwf, rwf_aux)}"
            )
        lines_out.append(f"    wf sleep assessment: {assess_wf_sleep(consys_parsed)}")
    else:
        lines_out.append("    (none in these kernel files; note: kernel_log_19 had 0 dumps, all in kernel_log_8)")
    lines_out.append("")


def parse_main_log(lines_out: list[str]) -> None:
    lines_out.append("=== main_log (25 zoom / main_log_14) ===")
    if not MAIN_LOG.exists():
        lines_out.append(f"  MISSING: {MAIN_LOG}")
        return

    mode0 = mode1 = 0
    zoom_first_ts = zoom_last_ts = None
    zoom_first_snip = zoom_last_snip = ""
    screen_on: list[str] = []
    screen_off: list[str] = []
    softap_hits: list[str] = []
    softap_keywords = ("AP-ENABLED", "startSoftAp", "StartSoftAp", "SOFTAP", "SoftAp")

    kernel_ts = None
    for path in KERNEL_FILES:
        if not path.exists():
            continue
        for line in iter_lines(path):
            if "kalPerMonUpdate" in line:
                mo = RE_TS.match(line)
                if mo:
                    kernel_ts = mo.group(1)
                    break
        if kernel_ts:
            break

    main_ts = None
    for line in iter_lines(MAIN_LOG):
        mo = RE_TS.match(line)
        if mo and main_ts is None:
            main_ts = mo.group(1)

        if "SETSUSPENDMODE" in line:
            sm = RE_SETSUSPEND.search(line)
            if sm:
                if sm.group(1) == "0":
                    mode0 += 1
                elif sm.group(1) == "1":
                    mode1 += 1

        if "us.zoom.videomeetings" in line and mo:
            if zoom_first_ts is None:
                zoom_first_ts = mo.group(1)
                zoom_first_snip = line.strip()[:140]
            zoom_last_ts = mo.group(1)
            zoom_last_snip = line.strip()[:140]

        if mo and ("SCREEN_ON" in line or "android.intent.action.SCREEN_ON" in line):
            screen_on.append(mo.group(1))
        if mo and ("SCREEN_OFF" in line or "android.intent.action.SCREEN_OFF" in line):
            screen_off.append(mo.group(1))

        if mo:
            for kw in softap_keywords:
                if kw in line:
                    softap_hits.append(f"{mo.group(1)}: {line.strip()[:160]}")
                    break

    lines_out.append(f"  SETSUSPENDMODE mode 0 (resume): {mode0}")
    lines_out.append(f"  SETSUSPENDMODE mode 1 (suspend): {mode1}")
    lines_out.append(
        f"  us.zoom.videomeetings log span: first={zoom_first_ts} last={zoom_last_ts}"
    )
    if zoom_first_snip:
        lines_out.append(f"    first line: {zoom_first_snip}")
    if zoom_last_snip:
        lines_out.append(f"    last line:  {zoom_last_snip}")

    lines_out.append(f"  SCREEN_ON events in main_log: {len(screen_on)}")
    if screen_on:
        lines_out.append(f"    times: {', '.join(screen_on)}")
    lines_out.append(f"  SCREEN_OFF events in main_log: {len(screen_off)}")
    if not screen_off:
        lines_out.append("    (none in this main_log segment)")

    lines_out.append(f"  SoftAP indicators (AP-ENABLED/startSoftAp/etc): {len(softap_hits)}")
    if softap_hits:
        for h in softap_hits[:10]:
            lines_out.append(f"    {h}")
    else:
        lines_out.append("    SoftAP not observed active during this main_log capture")

    lines_out.append("  Timestamp offset (kernel localtime vs main_log):")
    if kernel_ts and main_ts:
        lines_out.append(f"    sample kernel (kalPerMon): {kernel_ts}")
        lines_out.append(f"    sample main:             {main_ts}")
        from datetime import datetime

        fmt = "%m-%d %H:%M:%S.%f"
        kt = datetime.strptime(kernel_ts, fmt)
        mt = datetime.strptime(main_ts.split()[0] + " " + main_ts.split()[1], fmt)
        delta_h = (mt - kt).total_seconds() / 3600
        lines_out.append(
            f"    observed offset main - kernel ~ {delta_h:+.1f} h (kernel ~UTC, main ~local Asia/Shanghai)"
        )
    lines_out.append("")


def main() -> int:
    lines: list[str] = []
    lines.append("CN6OS16-2328 Zoom scenario WiFi metrics summary")
    lines.append("=" * 60)

    parse_kernels(KERNEL_FILES, "25 zoom (kernel 8 + 19)", lines)

    charge_kernels = find_zoom_charging_kernels()
    if charge_kernels:
        parse_kernels(charge_kernels, "25 zoom charging", lines)

    parse_main_log(lines)

    text = "\n".join(lines)
    OUT_PATH.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

