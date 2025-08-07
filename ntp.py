#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台 NTP 时间同步工具（本地时间显示版）

Features
--------
* 通过 UDP 实现纯 Python 的 NTP 客户端（不依赖第三方库）。
* 自动回退至备用 NTP 服务器列表。
* 支持在 Windows 与 Linux 上 **同步系统时间**（需要管理员/ROOT 权限）。
* `--set-system` 参数控制是否写入系统时间。
* `--debug` 打开调试日志。
* **所有时间均以本地时区显示**（而不是 UTC）。
* 完全符合 PEP‑8 / PEP‑257 / PEP‑484，适合 CI 检查。

Author  : ChatGPT (2025)
License : MIT
"""

import argparse
import ctypes
import logging
import os
import platform
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Protocol

# --------------------------------------------------------------
# 常量 & 数据类
# --------------------------------------------------------------
NTP_EPOCH = datetime(1900, 1, 1, tzinfo=timezone.utc)
UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NTP_DELTA = int((UNIX_EPOCH - NTP_EPOCH).total_seconds())   # 2208988800
DEFAULT_SERVERS = [
    "pool.ntp.org",
    "time.google.com",
    "time.windows.com",
]
DEFAULT_TIMEOUT = 5.0          # 秒
SYNC_THRESHOLD = 1.0          # 秒，差值大于该阈值才尝试同步系统时间


@dataclass
class NTPConfig:
    """运行时配置（可通过 CLI 覆盖）"""
    servers: List[str] = field(default_factory=lambda: DEFAULT_SERVERS.copy())
    timeout: float = DEFAULT_TIMEOUT
    version: int = 4                     # NTP 协议版本，4 为当前推荐
    sync_threshold: float = SYNC_THRESHOLD


# --------------------------------------------------------------
# 日志初始化
# --------------------------------------------------------------
def init_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


# --------------------------------------------------------------
# 抽象时间写入接口（跨平台统一入口）
# --------------------------------------------------------------
class TimeSetter(Protocol):
    """统一的“写入系统时间”协议，返回 True 表示成功，False 表示失败"""
    def set_system_time(self, unix_ts: float) -> bool:
        ...


# --------------------------------------------------------------
# Windows 实现（使用 WinAPI SetSystemTime）
# --------------------------------------------------------------
class WindowsTimeSetter:
    """通过 WinAPI SetSystemTime 写入本机时钟（仅在 Windows 上可用）。"""

    def set_system_time(self, unix_ts: float) -> bool:
        try:
            utc_dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)

            class SYSTEMTIME(ctypes.Structure):
                _fields_ = [
                    ("wYear", ctypes.c_ushort),
                    ("wMonth", ctypes.c_ushort),
                    ("wDayOfWeek", ctypes.c_ushort),   # 0 = Sunday
                    ("wDay", ctypes.c_ushort),
                    ("wHour", ctypes.c_ushort),
                    ("wMinute", ctypes.c_ushort),
                    ("wSecond", ctypes.c_ushort),
                    ("wMilliseconds", ctypes.c_ushort),
                ]

            st = SYSTEMTIME(
                wYear=utc_dt.year,
                wMonth=utc_dt.month,
                wDay=utc_dt.day,
                wDayOfWeek=(utc_dt.weekday() + 1) % 7,
                wHour=utc_dt.hour,
                wMinute=utc_dt.minute,
                wSecond=utc_dt.second,
                wMilliseconds=int(utc_dt.microsecond / 1000),
            )
            logging.debug("准备写入系统时间 (Windows UTC): %s", utc_dt.isoformat())
            if not ctypes.windll.kernel32.SetSystemTime(ctypes.byref(st)):
                err = ctypes.GetLastError()
                logging.error(
                    "SetSystemTime 调用失败，错误码 %d（请以管理员身份运行）", err
                )
                return False
            logging.info("系统时间已成功同步为 UTC %s", utc_dt.isoformat())
            return True
        except Exception:
            logging.exception("Windows 设置系统时间时发生异常")
            return False


# --------------------------------------------------------------
# Linux 实现（使用 clock_settime + 回退到 date 命令）
# --------------------------------------------------------------
class LinuxTimeSetter:
    """在 Linux/Unix 系统上写入系统时间（优先使用 libc.clock_settime）。"""

    CLOCK_REALTIME = 0  # clockid_t for CLOCK_REALTIME (POSIX)

    def _set_time_via_libc(self, unix_ts: float) -> bool:
        """直接调用 libc 的 clock_settime（需要 root）。"""
        try:
            class timespec(ctypes.Structure):
                _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

            ts = timespec()
            ts.tv_sec = int(unix_ts)
            ts.tv_nsec = int((unix_ts - ts.tv_sec) * 1_000_000_000)

            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            res = libc.clock_settime(self.CLOCK_REALTIME, ctypes.byref(ts))
            if res != 0:
                errno = ctypes.get_errno()
                logging.error(
                    "clock_settime 调用失败，errno=%d (%s)", errno, os.strerror(errno)
                )
                return False
            logging.info(
                "系统时间已通过 libc.clock_settime 成功同步（UTC %s）",
                datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat(),
            )
            return True
        except Exception:
            logging.exception("通过 libc 设置系统时间时出现异常")
            return False

    def _set_time_via_date_cmd(self, unix_ts: float) -> bool:
        """回退方案：使用 `sudo date -s "YYYY-MM-DD HH:MM:SS"`（需要 sudo）。"""
        utc_dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        # 将 UTC 时间转为本地时间字符串，date 命令默认使用本地时区
        local_str = utc_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        cmd = ["sudo", "date", "-s", local_str]
        logging.debug("尝试执行外部命令以设置时间: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info("系统时间已通过 `date` 命令同步（本地时间 %s）", local_str)
            return True
        except subprocess.CalledProcessError as e:
            logging.error(
                "使用 `date` 命令设置时间失败: %s\nstderr: %s", e, e.stderr.strip()
            )
            return False
        except FileNotFoundError:
            logging.error("`date` 命令未找到，无法在此平台上设置系统时间")
            return False

    def set_system_time(self, unix_ts: float) -> bool:
        """统一入口：先尝试 libc，若失败回退到 date 命令。"""
        if self._set_time_via_libc(unix_ts):
            return True
        return self._set_time_via_date_cmd(unix_ts)


# --------------------------------------------------------------
# 根据运行平台返回合适的 TimeSetter 实例
# --------------------------------------------------------------
def get_time_setter() -> Optional[TimeSetter]:
    """返回当前平台对应的 TimeSetter（None 表示平台不支持写入系统时间）"""
    current = platform.system().lower()
    if current == "windows":
        return WindowsTimeSetter()
    elif current in ("linux", "darwin", "freebsd", "openbsd", "netbsd"):
        return LinuxTimeSetter()
    else:
        logging.warning("未检测到对当前平台 (%s) 的系统时间写入实现", current)
        return None


# --------------------------------------------------------------
# NTP 客户端（查询部分保持不变，只是打印时改为本地时间）
# --------------------------------------------------------------
class NTPClient:
    """简洁的 UDP NTP 客户端"""

    def __init__(self, cfg: Optional[NTPConfig] = None):
        self.cfg = cfg or NTPConfig()
        self.port = 123

    # ----------------------------------------------------------
    # 1. 组装 NTP 请求报文（48 字节）
    # ----------------------------------------------------------
    def _build_packet(self) -> bytes:
        li = 0
        vn = self.cfg.version
        mode = 3
        first_byte = (li << 6) | (vn << 3) | mode
        packet = struct.pack("!B B B B 11I", first_byte, 0, 0, 0, *([0] * 11))
        return packet

    # ----------------------------------------------------------
    # 2. 发送请求并解析响应
    # ----------------------------------------------------------
    def get_ntp_time(self, server: str) -> Optional[float]:
        logging.debug("向 %s 发送 NTP 请求", server)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.cfg.timeout)
                sock.sendto(self._build_packet(), (server, self.port))
                data, _ = sock.recvfrom(512)
        except (socket.timeout, socket.gaierror) as exc:
            logging.warning("网络错误（%s）: %s", server, exc)
            return None
        except OSError as exc:
            logging.error("Socket 错误: %s", exc)
            return None

        if len(data) < 48:
            logging.warning("收到的 NTP 包长度不足 (%d < 48)", len(data))
            return None

        try:
            seconds, fraction = struct.unpack("!II", data[40:48])
        except struct.error as exc:
            logging.error("解析时间戳失败: %s", exc)
            return None

        ntp_timestamp = seconds + fraction / 2**32
        unix_timestamp = ntp_timestamp - NTP_DELTA
        return unix_timestamp

    # ----------------------------------------------------------
    # 3. 轮询服务器列表（带回退）
    # ----------------------------------------------------------
    def query(self, server: Optional[str] = None) -> Optional[float]:
        candidates = [server] if server else self.cfg.servers
        for srv in candidates:
            ts = self.get_ntp_time(srv)
            if ts is not None:
                return ts
        return None

    # ----------------------------------------------------------
    # 4. 同步（查询 +（可选）写入系统时间）
    # ----------------------------------------------------------
    def sync(
        self,
        server: Optional[str] = None,
        set_system: bool = False,
        time_setter: Optional[TimeSetter] = None,
    ) -> bool:
        """
        主流程：
        1. 查询 NTP 时间；
        2. 与本机时间比较，输出差值；
        3. 若 ``set_system`` 为 True 且差值 > 阈值，则尝试写入系统时间。
        """
        logging.info("查询 NTP 时间...")
        ntp_ts = self.query(server)
        if ntp_ts is None:
            logging.error("无法从任何 NTP 服务器获取时间")
            return False

        local_ts = time.time()
        diff = abs(ntp_ts - local_ts)

        # ---------- 本地时间显示 ----------
        # 将 UTC 时间转换为本地时区后打印
        local_tz = datetime.now().astimezone().tzinfo   # 当前系统时区
        ntp_local = datetime.fromtimestamp(ntp_ts, tz=local_tz)
        local_now = datetime.fromtimestamp(local_ts, tz=local_tz)

        logging.info("NTP 服务器时间（本地时区） : %s", ntp_local.strftime("%Y-%m-%d %H:%M:%S %Z"))
        logging.info("本机时间（本地时区）      : %s", local_now.strftime("%Y-%m-%d %H:%M:%S %Z"))
        logging.info("时间差                     : %.3f 秒", diff)

        if set_system:
            # 只有当差值超过阈值才写入系统时间
            if diff <= self.cfg.sync_threshold:
                logging.info(
                    "时间差小于 %.1f 秒，无需同步系统时间", self.cfg.sync_threshold
                )
                return True

            if time_setter is None:
                logging.error("当前平台不支持写入系统时间")
                return False

            logging.info("尝试同步系统时间（需要管理员/ROOT 权限）...")
            return time_setter.set_system_time(ntp_ts)

        logging.info("仅查询时间，未执行系统时间写入")
        return True


# --------------------------------------------------------------
# 参数解析
# --------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="跨平台 NTP 时间同步工具（本地时间显示版）"
    )
    parser.add_argument(
        "-s",
        "--server",
        help="指定单个 NTP 服务器（默认使用内部服务器列表）",
        default=None,
    )
    parser.add_argument(
        "-S",
        "--set-system",
        action="store_true",
        help="将系统时间同步到 NTP 时间（需要管理员/ROOT 权限）",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="打开调试日志",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="UDP 超时时间（秒），默认 %.1f" % DEFAULT_TIMEOUT,
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SYNC_THRESHOLD,
        help="同步阈值（秒），仅在时间差大于该值时才写系统时间",
    )
    return parser.parse_args()


# --------------------------------------------------------------
# 主入口
# --------------------------------------------------------------
def main() -> None:
    args = parse_args()
    init_logging(debug=args.debug)

    cfg = NTPConfig(
        timeout=args.timeout,
        sync_threshold=args.threshold,
    )
    client = NTPClient(cfg)

    time_setter = get_time_setter() if args.set_system else None

    try:
        ok = client.sync(
            server=args.server,
            set_system=args.set_system,
            time_setter=time_setter,
        )
    except KeyboardInterrupt:
        logging.warning("用户中断")
        sys.exit(130)   # 130 = 128 + SIGINT
    except Exception:
        logging.exception("同步过程中出现未捕获异常")
        sys.exit(1)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
