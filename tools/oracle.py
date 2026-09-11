from services.oracle_service import (
    test_connection,
    database_info,
    instance_info,
    pdbs,
    tablespaces,
    sessions,
    blocking_sessions,
)


ORACLE_TOOL_DESCRIPTIONS = {
    "oracle.connection":
        "Test connectivity to the configured Oracle database.",

    "oracle.database_info":
        "Return Oracle database name, DBID, open mode, database role, and CDB status.",

    "oracle.instance_info":
        "Return Oracle instance name, host, version, status, database status, and startup time.",

    "oracle.pdbs":
        "Return Oracle pluggable databases and their open/restricted status.",

    "oracle.tablespaces":
        "Return Oracle tablespace usage, total space, and free space.",

    "oracle.sessions":
        "Return Oracle session counts grouped by session status.",

    "oracle.blocking_sessions":
        "Return sessions currently involved in Oracle blocking activity.",
}


ORACLE_TOOLS = {
    "oracle.connection": test_connection,
    "oracle.database_info": database_info,
    "oracle.instance_info": instance_info,
    "oracle.pdbs": pdbs,
    "oracle.tablespaces": tablespaces,
    "oracle.sessions": sessions,
    "oracle.blocking_sessions": blocking_sessions,
}
