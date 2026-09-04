# from tools.linux import (
#     get_system_info,
#     get_cpu_usage,
#     get_memory_usage,
#     get_disk_usage,
# )


# TOOLS = {
#     "linux.system_info": {
#         "description": "Get basic Linux system information.",
#         "function": get_system_info,
#         "read_only": True,
#     },
#     "linux.cpu": {
#         "description": "Get current CPU usage and load averages.",
#         "function": get_cpu_usage,
#         "read_only": True,
#     },
#     "linux.memory": {
#         "description": "Get current memory and swap usage.",
#         "function": get_memory_usage,
#         "read_only": True,
#     },
#     "linux.disk": {
#         "description": "Get disk usage for mounted filesystems.",
#         "function": get_disk_usage,
#         "read_only": True,
#     },
# }


# def list_tools() -> list[dict]:
#     """
#     Return tool metadata without exposing Python function objects.
#     """

#     return [
#         {
#             "name": name,
#             "description": definition["description"],
#             "read_only": definition["read_only"],
#         }
#         for name, definition in TOOLS.items()
#     ]


# def execute_tool(name: str) -> dict:
#     """
#     Execute a registered tool by its exact name.

#     No arbitrary shell commands or dynamically supplied
#     Python functions are allowed.
#     """

#     tool = TOOLS.get(name)

#     if tool is None:
#         raise ValueError(f"Unknown tool: {name}")

#     if not tool["read_only"]:
#         raise PermissionError(
#             f"Tool '{name}' is not read-only"
#         )

#     result = tool["function"]()

#     return {
#         "tool": name,
#         "ok": True,
#         "result": result,
#     }



"""
Central registry for all AI-callable tools.

The registry is the security boundary between the AI layer
and the operating system.

Tools must be explicitly registered.

No arbitrary shell commands.
No arbitrary SQL.
"""

from tools.linux import LINUX_TOOLS


LINUX_TOOL_DESCRIPTIONS = {
    "linux.system_info":
        "Get hostname, OS distribution, OS version, kernel, architecture, CPU count, boot time and uptime.",
    "linux.cpu":
        "Get CPU utilization, user/system/idle/I/O wait percentages, CPU cores and 1/5/15 minute load averages.",
    "linux.memory":
        "Get RAM total, used, available, free, cached, buffers and memory utilization percentage.",
    "linux.swap":
        "Get swap total, used, free, utilization percentage and swap I/O activity.",
    "linux.load":
        "Get 1/5/15 minute system load averages and load normalized by CPU count.",
    "linux.disk":
        "Get mounted filesystem usage including device, mount point, filesystem type, total, used, free and utilization.",
    "linux.inodes":
        "Get inode usage for mounted filesystems to detect inode exhaustion.",
    "linux.top_processes":
        "Get top processes by CPU and memory including PID, process name, user, status and thread count.",
    "linux.process_summary":
        "Get total process count and counts of running, sleeping, stopped and zombie processes.",
    "linux.network_interfaces":
        "Get network interfaces, state, IPv4/IPv6 addresses, MAC address, MTU and link speed.",
    "linux.network_stats":
        "Get network RX/TX bytes, packets, errors and dropped packets for each interface.",
    "linux.listening_ports":
        "Get TCP and UDP listening ports and the associated process PID when available.",
    "linux.failed_services":
        "Get systemd services currently in failed state.",
    "linux.journal_errors":
        "Get recent error-level messages from the systemd journal.",
    "linux.failed_logins":
        "Get recent failed SSH authentication attempts from the system journal.",
    "linux.selinux":
        "Get SELinux enforcement status and detailed sestatus output.",
    "linux.firewall":
        "Get firewalld active state, default zone and active firewall zones.",
    "linux.logged_in_users":
        "Get users currently logged into the Linux system including terminal, remote host and login time.",
}


TOOLS = {}


# ---------------------------------------------------------------------------
# Linux tools
# ---------------------------------------------------------------------------

for name, function in LINUX_TOOLS.items():
    TOOLS[name] = {
        "description": LINUX_TOOL_DESCRIPTIONS.get(
            name,
            f"Read-only Linux diagnostic tool: {name}",
        ),
        "function": function,
        "read_only": True,
        "category": "linux",
    }


# ---------------------------------------------------------------------------
# Registry functions
# ---------------------------------------------------------------------------

def list_tools():
    """
    Return metadata for all registered tools.
    """
    result = []

    for name, metadata in TOOLS.items():
        result.append(
            {
                "name": name,
                "description": metadata["description"],
                "read_only": metadata["read_only"],
                "category": metadata["category"],
            }
        )

    return result


def execute_tool(name: str, **kwargs):
    """
    Execute a registered tool only.

    Arbitrary commands cannot be executed through this function.
    """
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")

    tool = TOOLS[name]

    if not tool["read_only"]:
        raise PermissionError(
            f"Tool '{name}' is not allowed in read-only mode"
        )

    function = tool["function"]

    return function(**kwargs)