<#
.SYNOPSIS
  调用联发科 Kernel log converter，为 kernel_log 生成 .localtime（行首 MM-DD HH:MM:SS.mmm，便于与 Android main_log 按分秒对照）。

.DESCRIPTION
  默认 EXE：$env:KERNEL_TIME_CONVERT_EXE，否则
  D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe

  用法（与官方一致）：
    kernel_time_convert.exe <kernel_log 文件 | 目录>

.EXAMPLE
  .\scripts\kernel_time_convert.ps1 -Path ".\OS162-34177\logs\...\kernel_log_6__2026_0331_224424"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)
$ErrorActionPreference = "Stop"
$exe = $env:KERNEL_TIME_CONVERT_EXE
if (-not $exe) {
    $exe = "D:\Program Files (x86)\Mediatek\Kernel log converter\kernel_time_convert.exe"
}
if (-not (Test-Path -LiteralPath $exe)) {
    Write-Error "kernel_time_convert.exe not found: $exe (set KERNEL_TIME_CONVERT_EXE)"
}
& $exe $Path
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    exit $LASTEXITCODE
}
