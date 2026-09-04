import os
import platform
import socket
import time

import psutil


def get_system_info() -> dict:
    """
    Read-only information about the Linux system.
    """

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(),
        "boot_time": time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(psutil.boot_time()),
        ),
    }


def get_cpu_usage() -> dict:
    """
    Read-only CPU information.
    """

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "load_avg_1": psutil.getloadavg()[0],
        "load_avg_5": psutil.getloadavg()[1],
        "load_avg_15": psutil.getloadavg()[2],
        "cpu_count": psutil.cpu_count(),
    }


def get_memory_usage() -> dict:
    """
    Read-only memory and swap information.
    """

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "memory": {
            "percent": memory.percent,
            "total_mb": round(memory.total / (1024 ** 2), 1),
            "used_mb": round(memory.used / (1024 ** 2), 1),
            "available_mb": round(memory.available / (1024 ** 2), 1),
        },
        "swap": {
            "percent": swap.percent,
            "total_mb": round(swap.total / (1024 ** 2), 1),
            "used_mb": round(swap.used / (1024 ** 2), 1),
        },
    }


def get_disk_usage() -> dict:
    """
    Read-only disk usage information.
    """

    result = {}

    for partition in psutil.disk_partitions(all=False):
        mountpoint = partition.mountpoint

        try:
            usage = psutil.disk_usage(mountpoint)
        except (PermissionError, OSError):
            continue

        result[mountpoint] = {
            "percent": usage.percent,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
        }

    return result