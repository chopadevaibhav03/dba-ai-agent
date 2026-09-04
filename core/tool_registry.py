from tools.linux import (
    get_system_info,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
)


TOOLS = {
    "linux.system_info": {
        "description": "Get basic Linux system information.",
        "function": get_system_info,
        "read_only": True,
    },
    "linux.cpu": {
        "description": "Get current CPU usage and load averages.",
        "function": get_cpu_usage,
        "read_only": True,
    },
    "linux.memory": {
        "description": "Get current memory and swap usage.",
        "function": get_memory_usage,
        "read_only": True,
    },
    "linux.disk": {
        "description": "Get disk usage for mounted filesystems.",
        "function": get_disk_usage,
        "read_only": True,
    },
}


def list_tools() -> list[dict]:
    """
    Return tool metadata without exposing Python function objects.
    """

    return [
        {
            "name": name,
            "description": definition["description"],
            "read_only": definition["read_only"],
        }
        for name, definition in TOOLS.items()
    ]


def execute_tool(name: str) -> dict:
    """
    Execute a registered tool by its exact name.

    No arbitrary shell commands or dynamically supplied
    Python functions are allowed.
    """

    tool = TOOLS.get(name)

    if tool is None:
        raise ValueError(f"Unknown tool: {name}")

    if not tool["read_only"]:
        raise PermissionError(
            f"Tool '{name}' is not read-only"
        )

    result = tool["function"]()

    return {
        "tool": name,
        "ok": True,
        "result": result,
    }