# import os
# import platform
# import socket
# import time

# import psutil


# def get_system_info() -> dict:
#     """
#     Read-only information about the Linux system.
#     """

#     return {
#         "hostname": socket.gethostname(),
#         "platform": platform.system(),
#         "platform_release": platform.release(),
#         "architecture": platform.machine(),
#         "cpu_count": psutil.cpu_count(),
#         "boot_time": time.strftime(
#             "%Y-%m-%dT%H:%M:%S",
#             time.localtime(psutil.boot_time()),
#         ),
#     }


# def get_cpu_usage() -> dict:
#     """
#     Read-only CPU information.
#     """

#     return {
#         "cpu_percent": psutil.cpu_percent(interval=0.5),
#         "load_avg_1": psutil.getloadavg()[0],
#         "load_avg_5": psutil.getloadavg()[1],
#         "load_avg_15": psutil.getloadavg()[2],
#         "cpu_count": psutil.cpu_count(),
#     }


# def get_memory_usage() -> dict:
#     """
#     Read-only memory and swap information.
#     """

#     memory = psutil.virtual_memory()
#     swap = psutil.swap_memory()

#     return {
#         "memory": {
#             "percent": memory.percent,
#             "total_mb": round(memory.total / (1024 ** 2), 1),
#             "used_mb": round(memory.used / (1024 ** 2), 1),
#             "available_mb": round(memory.available / (1024 ** 2), 1),
#         },
#         "swap": {
#             "percent": swap.percent,
#             "total_mb": round(swap.total / (1024 ** 2), 1),
#             "used_mb": round(swap.used / (1024 ** 2), 1),
#         },
#     }


# def get_disk_usage() -> dict:
#     """
#     Read-only disk usage information.
#     """

#     result = {}

#     for partition in psutil.disk_partitions(all=False):
#         mountpoint = partition.mountpoint

#         try:
#             usage = psutil.disk_usage(mountpoint)
#         except (PermissionError, OSError):
#             continue

#         result[mountpoint] = {
#             "percent": usage.percent,
#             "total_gb": round(usage.total / (1024 ** 3), 2),
#             "used_gb": round(usage.used / (1024 ** 3), 2),
#             "free_gb": round(usage.free / (1024 ** 3), 2),
#         }

#     return result




"""
Read-only Linux diagnostic tools.

All functions:
- are read-only
- return JSON-serializable dictionaries
- handle their own errors
- avoid arbitrary shell commands
- are intended for the Tool Registry / AI Orchestrator
"""

import os
import platform
import re
import socket
import subprocess
import time
from datetime import datetime

import psutil


DEFAULT_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_command(command, timeout=DEFAULT_TIMEOUT):
    """Run a fixed command safely and return stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "command timed out",
        }

    except Exception as exc:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
        }


def _gb(value):
    """Convert bytes to GB."""
    return round(value / (1024 ** 3), 2)


def _human_uptime(seconds):
    """Convert seconds into a readable uptime string."""
    seconds = int(seconds)

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# SYSTEM
# ---------------------------------------------------------------------------

def system_info() -> dict:
    """
    Return basic operating system and host information.
    """
    try:
        uname = platform.uname()
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        result = {
            "ok": True,
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "os": platform.system(),
            "distribution": "",
            "distribution_version": "",
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
            "uptime_seconds": round(uptime),
            "uptime_human": _human_uptime(uptime),
        }

        # RHEL / Linux distribution information
        try:
            os_release = {}

            with open("/etc/os-release", "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os_release[key] = value.strip('"')

            result["distribution"] = os_release.get("NAME", "")
            result["distribution_version"] = os_release.get("VERSION_ID", "")

        except Exception:
            pass

        return result

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

def cpu() -> dict:
    """
    Detailed CPU utilization and load information.
    """
    try:
        usage = psutil.cpu_percent(interval=1)

        times = psutil.cpu_times_percent(interval=0)

        try:
            load_1, load_5, load_15 = os.getloadavg()
        except (AttributeError, OSError):
            load_1 = load_5 = load_15 = None

        return {
            "ok": True,
            "usage_percent": round(usage, 2),
            "user_percent": round(getattr(times, "user", 0), 2),
            "system_percent": round(getattr(times, "system", 0), 2),
            "idle_percent": round(getattr(times, "idle", 0), 2),
            "iowait_percent": round(getattr(times, "iowait", 0), 2),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "load_1m": round(load_1, 2) if load_1 is not None else None,
            "load_5m": round(load_5, 2) if load_5 is not None else None,
            "load_15m": round(load_15, 2) if load_15 is not None else None,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# MEMORY
# ---------------------------------------------------------------------------

def memory() -> dict:
    """
    Detailed RAM usage.
    """
    try:
        vm = psutil.virtual_memory()

        return {
            "ok": True,
            "total_bytes": vm.total,
            "total_gb": _gb(vm.total),
            "used_bytes": vm.used,
            "used_gb": _gb(vm.used),
            "available_bytes": vm.available,
            "available_gb": _gb(vm.available),
            "free_bytes": vm.free,
            "free_gb": _gb(vm.free),
            "cached_bytes": getattr(vm, "cached", 0),
            "cached_gb": _gb(getattr(vm, "cached", 0)),
            "buffers_bytes": getattr(vm, "buffers", 0),
            "buffers_gb": _gb(getattr(vm, "buffers", 0)),
            "usage_percent": round(vm.percent, 2),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# SWAP
# ---------------------------------------------------------------------------

def swap() -> dict:
    """
    Detailed swap usage.
    """
    try:
        sw = psutil.swap_memory()

        return {
            "ok": True,
            "total_bytes": sw.total,
            "total_gb": _gb(sw.total),
            "used_bytes": sw.used,
            "used_gb": _gb(sw.used),
            "free_bytes": sw.free,
            "free_gb": _gb(sw.free),
            "usage_percent": round(sw.percent, 2),
            "sin_bytes": sw.sin,
            "sout_bytes": sw.sout,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------

def load() -> dict:
    """
    Return system load averages.
    """
    try:
        load_1, load_5, load_15 = os.getloadavg()

        logical_cpus = psutil.cpu_count(logical=True) or 1

        return {
            "ok": True,
            "load_1m": round(load_1, 2),
            "load_5m": round(load_5, 2),
            "load_15m": round(load_15, 2),
            "logical_cpus": logical_cpus,
            "load_1m_per_cpu": round(load_1 / logical_cpus, 2),
            "load_5m_per_cpu": round(load_5 / logical_cpus, 2),
            "load_15m_per_cpu": round(load_15 / logical_cpus, 2),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# DISK
# ---------------------------------------------------------------------------

def disk() -> dict:
    """
    Filesystem usage for mounted filesystems.
    """
    try:
        filesystems = []

        partitions = psutil.disk_partitions(all=False)

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)

                filesystems.append(
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_bytes": usage.total,
                        "total_gb": _gb(usage.total),
                        "used_bytes": usage.used,
                        "used_gb": _gb(usage.used),
                        "free_bytes": usage.free,
                        "free_gb": _gb(usage.free),
                        "usage_percent": round(usage.percent, 2),
                        "options": partition.opts,
                        "read_only": "ro" in partition.opts.split(","),
                    }
                )

            except (PermissionError, OSError):
                continue

        return {
            "ok": True,
            "filesystems": filesystems,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# INODES
# ---------------------------------------------------------------------------

def inodes() -> dict:
    """
    Return inode usage for mounted filesystems using df.
    """
    try:
        result = _run_command(
            ["df", "-Pi"],
            timeout=DEFAULT_TIMEOUT,
        )

        if result["returncode"] != 0:
            return {
                "ok": False,
                "error": result["stderr"][:500],
            }

        filesystems = []

        lines = result["stdout"].splitlines()

        for line in lines[1:]:
            parts = line.split()

            if len(parts) < 6:
                continue

            try:
                filesystems.append(
                    {
                        "filesystem": parts[0],
                        "inodes_total": int(parts[1]),
                        "inodes_used": int(parts[2]),
                        "inodes_free": int(parts[3]),
                        "inode_usage_percent": parts[4],
                        "mountpoint": parts[5],
                    }
                )
            except ValueError:
                continue

        return {
            "ok": True,
            "filesystems": filesystems,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# PROCESSES
# ---------------------------------------------------------------------------

def top_processes(n: int = 10) -> dict:
    """
    Top processes by CPU and memory usage.
    """
    try:
        n = max(1, min(int(n), 50))

        processes = []

        for process in psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "status",
                "memory_percent",
                "cpu_percent",
                "num_threads",
            ]
        ):
            try:
                info = process.info

                processes.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "username": info.get("username"),
                        "status": info.get("status"),
                        "memory_percent": round(
                            info.get("memory_percent") or 0,
                            2,
                        ),
                        "cpu_percent": round(
                            info.get("cpu_percent") or 0,
                            2,
                        ),
                        "threads": info.get("num_threads"),
                    }
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        by_cpu = sorted(
            processes,
            key=lambda x: x["cpu_percent"],
            reverse=True,
        )[:n]

        by_memory = sorted(
            processes,
            key=lambda x: x["memory_percent"],
            reverse=True,
        )[:n]

        return {
            "ok": True,
            "process_count": len(processes),
            "top_by_cpu": by_cpu,
            "top_by_memory": by_memory,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def process_summary() -> dict:
    """
    Process state summary.
    """
    try:
        counts = {
            "running": 0,
            "sleeping": 0,
            "stopped": 0,
            "zombie": 0,
            "other": 0,
        }

        total = 0

        for process in psutil.process_iter(["status"]):
            try:
                status = process.info.get("status")
                total += 1

                if status == psutil.STATUS_RUNNING:
                    counts["running"] += 1
                elif status in (
                    psutil.STATUS_SLEEPING,
                    psutil.STATUS_IDLE,
                ):
                    counts["sleeping"] += 1
                elif status == psutil.STATUS_STOPPED:
                    counts["stopped"] += 1
                elif status == psutil.STATUS_ZOMBIE:
                    counts["zombie"] += 1
                else:
                    counts["other"] += 1

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        return {
            "ok": True,
            "total": total,
            **counts,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# NETWORK
# ---------------------------------------------------------------------------

def network_interfaces() -> dict:
    """
    Network interfaces, addresses and state.
    """
    try:
        interfaces = []

        addresses = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for interface, addr_list in addresses.items():
            interface_info = {
                "interface": interface,
                "state": "UNKNOWN",
                "speed_mbps": 0,
                "mtu": None,
                "ipv4": [],
                "ipv6": [],
                "mac": None,
            }

            if interface in stats:
                interface_info["state"] = (
                    "UP" if stats[interface].isup else "DOWN"
                )
                interface_info["speed_mbps"] = stats[interface].speed
                interface_info["mtu"] = stats[interface].mtu

            for addr in addr_list:

                if addr.family == socket.AF_INET:
                    interface_info["ipv4"].append(
                        {
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                        }
                    )

                elif addr.family == socket.AF_INET6:
                    interface_info["ipv6"].append(
                        {
                            "address": addr.address,
                            "netmask": addr.netmask,
                        }
                    )

                else:
                    # Linux MAC address family
                    if str(addr.family).endswith("AF_PACKET"):
                        interface_info["mac"] = addr.address

            interfaces.append(interface_info)

        return {
            "ok": True,
            "interfaces": interfaces,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def network_stats() -> dict:
    """
    Network RX/TX statistics for all interfaces.
    """
    try:
        stats = psutil.net_io_counters(pernic=True)

        interfaces = []

        for interface, data in stats.items():
            interfaces.append(
                {
                    "interface": interface,
                    "rx_bytes": data.bytes_recv,
                    "tx_bytes": data.bytes_sent,
                    "rx_packets": data.packets_recv,
                    "tx_packets": data.packets_sent,
                    "rx_errors": data.errin,
                    "tx_errors": data.errout,
                    "rx_dropped": data.dropin,
                    "tx_dropped": data.dropout,
                }
            )

        return {
            "ok": True,
            "interfaces": interfaces,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def listening_ports() -> dict:
    """
    TCP/UDP ports currently listening.
    """
    try:
        connections = psutil.net_connections(kind="inet")

        listening = []

        for conn in connections:
            if conn.status not in (
                psutil.CONN_LISTEN,
                psutil.CONN_NONE,
            ):
                continue

            local = conn.laddr

            if not local:
                continue

            listening.append(
                {
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "address": local.ip,
                    "port": local.port,
                    "status": conn.status,
                    "pid": conn.pid,
                }
            )

        listening.sort(
            key=lambda x: (
                x["port"],
                x["address"],
            )
        )

        return {
            "ok": True,
            "count": len(listening),
            "listening": listening,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# SERVICES
# ---------------------------------------------------------------------------

def failed_services() -> dict:
    """
    Return systemd services currently in failed state.
    """
    try:
        result = _run_command(
            [
                "systemctl",
                "--failed",
                "--no-legend",
                "--no-pager",
            ]
        )

        if result["returncode"] not in (0, 1):
            return {
                "ok": False,
                "error": result["stderr"][:500],
            }

        services = []

        for line in result["stdout"].splitlines():
            parts = line.split(None, 4)

            if not parts:
                continue

            services.append(
                {
                    "unit": parts[0],
                    "raw": line.strip(),
                }
            )

        return {
            "ok": True,
            "failed_count": len(services),
            "services": services,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# JOURNAL
# ---------------------------------------------------------------------------

def journal_errors(n: int = 20) -> dict:
    """
    Recent error-level journal entries.
    """
    try:
        n = max(1, min(int(n), 100))

        result = _run_command(
            [
                "journalctl",
                "-p",
                "err",
                "-n",
                str(n),
                "--no-pager",
                "-o",
                "short-iso",
            ]
        )

        if result["returncode"] != 0:
            return {
                "ok": False,
                "error": result["stderr"][:500],
            }

        entries = [
            line
            for line in result["stdout"].splitlines()
            if line.strip()
        ]

        return {
            "ok": True,
            "count": len(entries),
            "errors": entries,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------

def failed_logins(n: int = 10) -> dict:
    """
    Recent failed SSH authentication attempts.
    """
    try:
        n = max(1, min(int(n), 100))

        result = _run_command(
            [
                "journalctl",
                "-u",
                "sshd",
                "-n",
                "500",
                "--no-pager",
            ]
        )

        if result["returncode"] != 0:
            return {
                "ok": False,
                "error": result["stderr"][:500],
            }

        matches = []

        for line in result["stdout"].splitlines():
            if (
                "Failed password" in line
                or "authentication failure" in line
                or "Invalid user" in line
            ):
                matches.append(line)

        return {
            "ok": True,
            "count": len(matches),
            "failed_logins": matches[-n:],
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def selinux() -> dict:
    """
    SELinux status.
    """
    try:
        getenforce = _run_command(["getenforce"])

        sestatus = _run_command(["sestatus"])

        if getenforce["returncode"] != 0:
            return {
                "ok": False,
                "error": getenforce["stderr"][:500],
            }

        status = getenforce["stdout"].strip()

        result = {
            "ok": True,
            "status": status,
            "enforcing": status.lower() == "enforcing",
            "sestatus": sestatus["stdout"],
        }

        return result

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def firewall() -> dict:
    """
    Read-only firewalld status.
    """
    try:
        state = _run_command(
            [
                "systemctl",
                "is-active",
                "firewalld",
            ]
        )

        active = state["stdout"].strip() == "active"

        result = {
            "ok": True,
            "active": active,
            "state": state["stdout"].strip(),
            "default_zone": None,
            "zones": [],
        }

        if not active:
            return result

        default_zone = _run_command(
            ["firewall-cmd", "--get-default-zone"]
        )

        if default_zone["returncode"] == 0:
            result["default_zone"] = default_zone["stdout"].strip()

        zones = _run_command(
            ["firewall-cmd", "--get-active-zones"]
        )

        if zones["returncode"] == 0:
            result["zones_raw"] = zones["stdout"]

        return result

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def logged_in_users() -> dict:
    """
    Currently logged-in users.
    """
    try:
        users = []

        for user in psutil.users():
            users.append(
                {
                    "username": user.name,
                    "terminal": user.terminal,
                    "host": user.host,
                    "started": datetime.fromtimestamp(
                        user.started
                    ).isoformat(),
                    "pid": user.pid,
                }
            )

        return {
            "ok": True,
            "count": len(users),
            "users": users,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# TOOL EXPORTS
# ---------------------------------------------------------------------------

LINUX_TOOLS = {
    "linux.system_info": system_info,
    "linux.cpu": cpu,
    "linux.memory": memory,
    "linux.swap": swap,
    "linux.load": load,
    "linux.disk": disk,
    "linux.inodes": inodes,
    "linux.top_processes": top_processes,
    "linux.process_summary": process_summary,
    "linux.network_interfaces": network_interfaces,
    "linux.network_stats": network_stats,
    "linux.listening_ports": listening_ports,
    "linux.failed_services": failed_services,
    "linux.journal_errors": journal_errors,
    "linux.failed_logins": failed_logins,
    "linux.selinux": selinux,
    "linux.firewall": firewall,
    "linux.logged_in_users": logged_in_users,
}


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "system": system_info(),
                "cpu": cpu(),
                "memory": memory(),
                "swap": swap(),
                "load": load(),
                "disk": disk(),
                "processes": top_processes(5),
                "services": failed_services(),
                "selinux": selinux(),
            },
            indent=2,
        )
    )