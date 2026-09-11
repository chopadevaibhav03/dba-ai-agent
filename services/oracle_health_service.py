from core.tool_registry import execute_tool


def _tool_result(tool_name):
    """
    Execute a registered read-only tool.

    The current tool registry returns the tool's raw result
    directly, so no result/ok wrapper is expected here.
    """
    return execute_tool(tool_name)


def _status_from_usage(usage_percent):
    if usage_percent >= 95:
        return "critical"

    if usage_percent >= 85:
        return "warning"

    return "healthy"


def get_oracle_health():
    findings = []
    errors = []

    # ---------------------------------------------------------
    # Connection
    # ---------------------------------------------------------

    try:
        connection = _tool_result("oracle.connection")

    except Exception as exc:
        return {
            "status": "critical",
            "critical_count": 1,
            "warning_count": 0,
            "findings": [
                {
                    "severity": "critical",
                    "source": "connection",
                    "message": f"Oracle connection failed: {exc}",
                }
            ],
            "errors": [],
            "connection": None,
        }

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    try:
        database = _tool_result("oracle.database_info")

        if database:
            db = database[0]

            if db.get("open_mode") != "READ WRITE":
                findings.append(
                    {
                        "severity": "warning",
                        "source": "database",
                        "message": (
                            f"Database {db.get('name')} is "
                            f"{db.get('open_mode')}"
                        ),
                    }
                )

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.database_info",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # Instance
    # ---------------------------------------------------------

    try:
        instance = _tool_result("oracle.instance_info")

        if instance:
            inst = instance[0]

            if inst.get("status") != "OPEN":
                findings.append(
                    {
                        "severity": "critical",
                        "source": "instance",
                        "message": (
                            f"Oracle instance is "
                            f"{inst.get('status')}"
                        ),
                    }
                )

            if inst.get("database_status") != "ACTIVE":
                findings.append(
                    {
                        "severity": "warning",
                        "source": "instance",
                        "message": (
                            f"Oracle database status is "
                            f"{inst.get('database_status')}"
                        ),
                    }
                )

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.instance_info",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # PDBs
    # ---------------------------------------------------------

    try:
        pdb_list = _tool_result("oracle.pdbs")

        for pdb in pdb_list or []:
            name = pdb.get("name")

            if name == "PDB$SEED":
                continue

            if pdb.get("open_mode") != "READ WRITE":
                findings.append(
                    {
                        "severity": "warning",
                        "source": "pdb",
                        "message": (
                            f"PDB {name} is "
                            f"{pdb.get('open_mode')}"
                        ),
                    }
                )

            if pdb.get("restricted") == "YES":
                findings.append(
                    {
                        "severity": "warning",
                        "source": "pdb",
                        "message": (
                            f"PDB {name} is in restricted mode"
                        ),
                    }
                )

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.pdbs",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # Tablespaces
    # ---------------------------------------------------------

    try:
        tablespace_list = _tool_result("oracle.tablespaces")

        for tablespace in tablespace_list or []:
            usage = float(
                tablespace.get("usage_percent", 0)
            )

            severity = _status_from_usage(usage)

            if severity != "healthy":
                findings.append(
                    {
                        "severity": severity,
                        "source": "tablespace",
                        "message": (
                            f"Tablespace "
                            f"{tablespace.get('tablespace_name')} "
                            f"is {usage:.2f}% full"
                        ),
                        "tablespace": tablespace.get(
                            "tablespace_name"
                        ),
                        "usage_percent": usage,
                    }
                )

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.tablespaces",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # Sessions
    # ---------------------------------------------------------

    try:
        _tool_result("oracle.sessions")

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.sessions",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # Blocking sessions
    # ---------------------------------------------------------

    try:
        blocking = _tool_result(
            "oracle.blocking_sessions"
        )

        if blocking:
            findings.append(
                {
                    "severity": "warning",
                    "source": "blocking_sessions",
                    "message": (
                        f"{len(blocking)} blocking session "
                        f"relationship(s) detected"
                    ),
                    "count": len(blocking),
                }
            )

    except Exception as exc:
        errors.append(
            {
                "tool": "oracle.blocking_sessions",
                "error": str(exc),
            }
        )

    # ---------------------------------------------------------
    # Errors are themselves a health concern
    # ---------------------------------------------------------

    if errors:
        findings.append(
            {
                "severity": "critical",
                "source": "health_check",
                "message": (
                    f"{len(errors)} Oracle health check "
                    f"tool(s) failed"
                ),
            }
        )

    # ---------------------------------------------------------
    # Final status
    # ---------------------------------------------------------

    critical_count = sum(
        1
        for finding in findings
        if finding["severity"] == "critical"
    )

    warning_count = sum(
        1
        for finding in findings
        if finding["severity"] == "warning"
    )

    if critical_count:
        status = "critical"
    elif warning_count:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "findings": findings,
        "errors": errors,
        "connection": connection,
    }
