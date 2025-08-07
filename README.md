# NTP Time Synchronization Tool

A cross-platform NTP time synchronization tool implemented in pure Python, displaying time in local timezone.

## Features

* Pure Python NTP client implementation via UDP (no third-party dependencies)
* Automatic fallback to backup NTP server list
* Support for **system time synchronization** on both Windows and Linux (requires administrator/ROOT privileges)
* `--set-system` parameter controls whether to write to system time
* `--debug` option to enable debug logging
* **All times are displayed in local timezone** (not UTC)
* Fully compliant with PEP‑8 / PEP‑257 / PEP‑484, suitable for CI checks

## Usage

```bash
# Basic usage - just query NTP time
python ntp.py

# Specify a custom NTP server
python ntp.py --server pool.ntp.org

# Synchronize system time (requires admin/root privileges)
python ntp.py --set-system

# Enable debug logging
python ntp.py --debug

# Set custom timeout and threshold
python ntp.py --timeout 3.0 --threshold 0.5
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-s`, `--server` | Specify a single NTP server (defaults to internal server list) |
| `-S`, `--set-system` | Synchronize system time to NTP time (requires admin/root privileges) |
| `-d`, `--debug` | Enable debug logging |
| `--timeout` | UDP timeout in seconds (default: 5.0) |
| `--threshold` | Synchronization threshold in seconds (default: 1.0) |

## Default NTP Servers

The tool uses the following NTP servers by default:
- pool.ntp.org
- time.google.com
- time.windows.com

## Platform Support

- **Windows**: Uses WinAPI `SetSystemTime` for system time synchronization
- **Linux/Unix**: Uses `libc.clock_settime` with fallback to `date` command
- **macOS**: Supported via the Linux/Unix implementation

## Requirements

- Python 3.7 or higher
- Administrator/ROOT privileges (only for system time synchronization)

## License

MIT