"""
Aggregated Linux health service.

This service does not execute arbitrary shell commands.
It calls only explicitly registered read-only Linux tools.
"""

from core.tool_registry import execute_tool


LINUX_HEALTH_TOOLS = {
    "system": "linux.system_info",
    "cpu": "linux.cpu",
    "memory": "linux.memory",
    "swap": "linux.swap",
    "load": "linux.load",
    "disk": "linux.disk",
    "inodes": "linux.inodes",
    "top_processes": "linux.top_processes",
    "process_summary": "linux.process_summary",
    "network_interfaces": "linux.network_interfaces",
    "network_stats": "linux.network_stats",
    "listening_ports": "linux.listening_ports",
    "failed_services": "linux.failed_services",
    "journal_errors": "linux.journal_errors",
    "failed_logins": "linux.failed_logins",
    "selinux": "linux.selinux",
    "firewall": "linux.firewall",
    "logged_in_users": "linux.logged_in_users",
}


def _run_tool(tool_name: str) -> dict:
    """
    Execute one registered read-only tool.

    Errors are isolated so one broken diagnostic does not
    prevent the complete Linux health response.
    """
    try:
        result = execute_tool(tool_name)

        if isinstance(result, dict):
            return result

        return {
            "ok": True,
            "data": result,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def _persistent_disk_warnings(disk_data: dict) -> list:
    """
    Identify genuinely concerning persistent filesystem usage.

    Installation media / ISO mounts should not be treated as
    server disk failures merely because they report 100%.
    """

    warnings = []

    if not isinstance(disk_data, dict):
        return warnings

    ignored_mount_patterns = (
        "/run/media/",
        "/media/",
        "/mnt/",
        "/dev/",
        "/proc/",
        "/sys/",
        "/run/",
    )

    for mount, info in disk_data.items():

        if not isinstance(info, dict):
            continue

        if any(mount.startswith(pattern)
               for pattern in ignored_mount_patterns):
            continue

        percent = info.get("percent")

        if percent is None:
            percent = info.get("usage_percent")

        if percent is None:
            continue

        try:
            percent = float(percent)
        except (TypeError, ValueError):
            continue

        if percent >= 95:
            warnings.append({
                "mount": mount,
                "usage_percent": round(percent, 1),
                "severity": "critical",
            })

        elif percent >= 85:
            warnings.append({
                "mount": mount,
                "usage_percent": round(percent, 1),
                "severity": "warning",
            })

    return warnings


def _calculate_health(data: dict) -> dict:
    """
    Calculate a deterministic Linux health summary.

    The LLM is NOT used for this calculation.
    """

    warnings = []
    critical = []

    cpu = data.get("cpu", {})
    memory = data.get("memory", {})
    swap = data.get("swap", {})
    disk = data.get("disk", {})
    services = data.get("failed_services", {})
    selinux = data.get("selinux", {})
    firewall = data.get("firewall", {})

    # CPU
    cpu_percent = cpu.get("usage_percent")

    if cpu_percent is not None:
        try:
            cpu_percent = float(cpu_percent)

            if cpu_percent >= 95:
                critical.append({
                    "type": "cpu",
                    "message": f"CPU utilization is {cpu_percent:.1f}%",
                })

            elif cpu_percent >= 85:
                warnings.append({
                    "type": "cpu",
                    "message": f"CPU utilization is {cpu_percent:.1f}%",
                })

        except (TypeError, ValueError):
            pass

    # Memory
    memory_percent = memory.get("usage_percent")

    if memory_percent is None:
        memory_percent = memory.get("percent")

    if memory_percent is not None:
        try:
            memory_percent = float(memory_percent)

            if memory_percent >= 95:
                critical.append({
                    "type": "memory",
                    "message": f"Memory utilization is {memory_percent:.1f}%",
                })

            elif memory_percent >= 85:
                warnings.append({
                    "type": "memory",
                    "message": f"Memory utilization is {memory_percent:.1f}%",
                })

        except (TypeError, ValueError):
            pass

    # Swap
    swap_percent = swap.get("usage_percent")

    if swap_percent is None:
        swap_percent = swap.get("percent")

    if swap_percent is not None:
        try:
            swap_percent = float(swap_percent)

            if swap_percent >= 90:
                warnings.append({
                    "type": "swap",
                    "message": f"Swap utilization is {swap_percent:.1f}%",
                })

        except (TypeError, ValueError):
            pass

    # Disk
    disk_warnings = _persistent_disk_warnings(disk)

    for item in disk_warnings:
        if item["severity"] == "critical":
            critical.append({
                "type": "disk",
                "message": (
                    f"{item['mount']} is "
                    f"{item['usage_percent']:.1f}% full"
                ),
            })
        else:
            warnings.append({
                "type": "disk",
                "message": (
                    f"{item['mount']} is "
                    f"{item['usage_percent']:.1f}% full"
                ),
            })

    # Failed services
    if isinstance(services, dict):

        failed = services.get("failed_services")

        if failed is None:
            failed = services.get("services")

        if isinstance(failed, list) and failed:
            critical.append({
                "type": "services",
                "message": f"{len(failed)} systemd service(s) are failed",
            })

    # SELinux
    if isinstance(selinux, dict):

        enforcing = selinux.get("enforcing")

        if enforcing is False:
            warnings.append({
                "type": "selinux",
                "message": "SELinux is not currently enforcing",
            })

    # Firewall
    if isinstance(firewall, dict):

        active = firewall.get("active")

        if active is False:
            warnings.append({
                "type": "firewall",
                "message": "Firewall does not appear to be active",
            })

    if critical:
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "critical": critical,
        "warnings": warnings,
    }


def get_linux_health() -> dict:
    """
    Collect the complete read-only Linux health snapshot.
    """

    data = {}

    for section, tool_name in LINUX_HEALTH_TOOLS.items():
        data[section] = _run_tool(tool_name)

    health = _calculate_health(data)

    return {
        "ok": True,
        "health": health,
        "data": data,
    }
