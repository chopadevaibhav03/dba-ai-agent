"""
Central registry for all AI-callable tools.

The registry is the security boundary between the AI layer
and the operating system.

Tools must be explicitly registered.

No arbitrary shell commands.
No arbitrary SQL.
"""

from tools.oscap import OSCAP_TOOLS
from tools.linux import LINUX_TOOLS
from tools.oracle import ORACLE_TOOLS, ORACLE_TOOL_DESCRIPTIONS


# ---------------------------------------------------------------------------
# Linux tool descriptions
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Parameter schemas
# ---------------------------------------------------------------------------

NO_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
}


OSCAP_PARAMETER_SCHEMAS = {
    "oscap.content": NO_PARAMETERS,

    "oscap.scan_status": {
        "type": "object",
        "properties": {
            "scan_id": {
                "type": "string",
                "description": "The OSCAP scan ID to inspect.",
            }
        },
        "required": ["scan_id"],
    },

    "oscap.findings_history": {
        "type": "object",
        "properties": {
            "scan_id": {
                "type": "string",
                "description": "Optional OSCAP scan ID. If omitted, use available findings history.",
            }
        },
        "required": [],
    },

    "oscap.report": {
        "type": "object",
        "properties": {
            "scan_id": {
                "type": "string",
                "description": "The OSCAP scan ID whose report should be retrieved.",
            }
        },
        "required": ["scan_id"],
    },

    "oscap.fix_preview": {
        "type": "object",
        "properties": {
            "scan_id": {
                "type": "string",
                "description": "The OSCAP scan ID containing the finding.",
            },
            "rule_id": {
                "type": "string",
                "description": "The OSCAP rule ID for which the remediation is being previewed.",
            },
        },
        "required": ["scan_id", "rule_id"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOLS = {}

# OSCAP
for name, definition in OSCAP_TOOLS.items():
    TOOLS[name] = {
        **definition,
        "category": "oscap",
        "parameters": OSCAP_PARAMETER_SCHEMAS.get(
            name,
            NO_PARAMETERS,
        ),
    }


# Linux
for name, function in LINUX_TOOLS.items():
    TOOLS[name] = {
        "description": LINUX_TOOL_DESCRIPTIONS.get(
            name,
            f"Read-only Linux diagnostic tool: {name}",
        ),
        "function": function,
        "read_only": True,
        "category": "linux",
        "parameters": NO_PARAMETERS,
    }


# Oracle
for name, function in ORACLE_TOOLS.items():
    TOOLS[name] = {
        "description": ORACLE_TOOL_DESCRIPTIONS.get(
            name,
            f"Read-only Oracle diagnostic tool: {name}",
        ),
        "function": function,
        "read_only": True,
        "category": "oracle",
        "parameters": NO_PARAMETERS,
    }


# ---------------------------------------------------------------------------
# Registry functions
# ---------------------------------------------------------------------------

def list_tools():
    """
    Return metadata for all registered tools.

    Python function objects are intentionally not exposed.
    """

    result = []

    for name, metadata in TOOLS.items():
        result.append(
            {
                "name": name,
                "description": metadata["description"],
                "read_only": metadata["read_only"],
                "category": metadata["category"],
                "parameters": metadata["parameters"],
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