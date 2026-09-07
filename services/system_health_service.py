from services.linux_health_service import get_linux_health
from services.oracle_health_service import get_oracle_health


def _overall_status(*statuses):
    statuses = {status for status in statuses if status}

    if "critical" in statuses:
        return "critical"

    if "warning" in statuses:
        return "warning"

    return "healthy"


def get_system_health():
    linux = get_linux_health()
    oracle = get_oracle_health()

    critical_count = (
        linux.get("critical_count", 0)
        + oracle.get("critical_count", 0)
    )

    warning_count = (
        linux.get("warning_count", 0)
        + oracle.get("warning_count", 0)
    )

    return {
        "status": _overall_status(
            linux.get("status"),
            oracle.get("status"),
        ),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "linux": linux,
        "oracle": oracle,
    }
