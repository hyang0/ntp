# NTP 时间同步工具

一个跨平台的 NTP 时间同步工具，使用纯 Python 实现，以本地时区显示时间。

## 功能特点

* 通过 UDP 实现纯 Python 的 NTP 客户端（不依赖第三方库）
* 自动回退至备用 NTP 服务器列表
* 支持在 Windows 与 Linux 上**同步系统时间**（需要管理员/ROOT 权限）
* `--set-system` 参数控制是否写入系统时间
* `--debug` 打开调试日志
* **所有时间均以本地时区显示**（而不是 UTC）
* 完全符合 PEP‑8 / PEP‑257 / PEP‑484，适合 CI 检查

## 使用方法

```bash
# 基本用法 - 仅查询 NTP 时间
python ntp.py

# 指定自定义 NTP 服务器
python ntp.py --server pool.ntp.org

# 同步系统时间（需要管理员/root权限）
python ntp.py --set-system

# 启用调试日志
python ntp.py --debug

# 设置自定义超时和阈值
python ntp.py --timeout 3.0 --threshold 0.5
```

## 命令行选项

| 选项 | 描述 |
|--------|-------------|
| `-s`, `--server` | 指定单个 NTP 服务器（默认使用内部服务器列表） |
| `-S`, `--set-system` | 将系统时间同步到 NTP 时间（需要管理员/ROOT 权限） |
| `-d`, `--debug` | 打开调试日志 |
| `--timeout` | UDP 超时时间（秒），默认 5.0 |
| `--threshold` | 同步阈值（秒），仅在时间差大于该值时才写系统时间，默认 1.0 |

## 默认 NTP 服务器

该工具默认使用以下 NTP 服务器：
- pool.ntp.org
- time.google.com
- time.windows.com

## 平台支持

- **Windows**：使用 WinAPI `SetSystemTime` 进行系统时间同步
- **Linux/Unix**：使用 `libc.clock_settime`，如失败则回退到 `date` 命令
- **macOS**：通过 Linux/Unix 实现支持

## 系统要求

- Python 3.7 或更高版本
- 管理员/ROOT 权限（仅用于系统时间同步）

## 许可证

MIT