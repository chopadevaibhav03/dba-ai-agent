import os
from typing import Any, Dict, List

import oracledb


class OracleConfigurationError(Exception):
    """Raised when Oracle connection configuration is missing."""


class OracleConnectionError(Exception):
    """Raised when an Oracle connection cannot be established."""


def get_connection():
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")

    missing = []

    if not user:
        missing.append("ORACLE_USER")

    if not password:
        missing.append("ORACLE_PASSWORD")

    if not dsn:
        missing.append("ORACLE_DSN")

    if missing:
        raise OracleConfigurationError(
            f"Missing Oracle configuration: {', '.join(missing)}"
        )

    try:
        return oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
        )
    except oracledb.Error as exc:
        raise OracleConnectionError(
            f"Unable to connect to Oracle: {exc}"
        ) from exc


def _query(sql: str) -> List[Dict[str, Any]]:
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(sql)

        columns = [column[0].lower() for column in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        cursor.close()
        connection.close()


def test_connection() -> Dict[str, Any]:
    rows = _query("""
        SELECT
            sys_context('USERENV', 'DB_NAME') AS db_name,
            sys_context('USERENV', 'SERVICE_NAME') AS service_name,
            sys_context('USERENV', 'INSTANCE_NAME') AS instance_name
        FROM dual
    """)

    return {
        "connected": True,
        **rows[0],
    }


def database_info() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            name,
            dbid,
            open_mode,
            database_role,
            cdb
        FROM v$database
    """)


def instance_info() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            instance_name,
            host_name,
            version,
            status,
            database_status,
            startup_time
        FROM v$instance
    """)


def pdbs() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            con_id,
            name,
            open_mode,
            restricted
        FROM v$pdbs
        ORDER BY con_id
    """)


def tablespaces() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            df.tablespace_name,
            ROUND(
                (df.total_mb - NVL(fs.free_mb, 0))
                / NULLIF(df.total_mb, 0) * 100,
                2
            ) AS usage_percent,
            df.total_mb,
            NVL(fs.free_mb, 0) AS free_mb
        FROM
            (
                SELECT
                    tablespace_name,
                    SUM(bytes) / 1024 / 1024 AS total_mb
                FROM dba_data_files
                GROUP BY tablespace_name
            ) df
        LEFT JOIN
            (
                SELECT
                    tablespace_name,
                    SUM(bytes) / 1024 / 1024 AS free_mb
                FROM dba_free_space
                GROUP BY tablespace_name
            ) fs
        ON df.tablespace_name = fs.tablespace_name
        ORDER BY usage_percent DESC
    """)


def sessions() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            status,
            COUNT(*) AS session_count
        FROM v$session
        GROUP BY status
        ORDER BY status
    """)


def blocking_sessions() -> List[Dict[str, Any]]:
    return _query("""
        SELECT
            blocking_session,
            sid,
            serial#,
            username,
            event,
            seconds_in_wait
        FROM v$session
        WHERE blocking_session IS NOT NULL
        ORDER BY blocking_session, sid
    """)
