"""各 SQL 方言的行数限制片段生成（探查/诊断 SQL 共用）。"""

from __future__ import annotations

import re


def clamp_row_limit(limit: int, *, max_limit: int = 20) -> int:
    return max(1, min(int(limit), max_limit))


def apply_dialect_row_limit(
    select_sql: str,
    *,
    dialect: str,
    limit: int,
    max_limit: int = 20,
) -> str:
    """
    为完整 SELECT 语句追加方言正确的行数上限。

    - Oracle：外层 ROWNUM 子查询（兼容 11g，避免 ROWNUM 与内层 WHERE 顺序问题）
    - SQL Server：SELECT TOP N
    - MySQL / ClickHouse / PostgreSQL 等：LIMIT N
    """
    base = str(select_sql or "").strip().rstrip(";")
    if not base:
        return base
    safe_limit = clamp_row_limit(limit, max_limit=max_limit)
    dialect_lower = str(dialect or "clickhouse").lower()

    if "oracle" in dialect_lower:
        return f"SELECT * FROM ({base}) WHERE ROWNUM <= {safe_limit}"

    if any(token in dialect_lower for token in ("sqlserver", "mssql", "tsql")):
        if re.search(r"(?is)\btop\s+\d+\b", base):
            return base
        return re.sub(r"(?is)^\s*select\s+", f"SELECT TOP {safe_limit} ", base, count=1)

    upper = base.upper()
    if " LIMIT " in f" {upper} " or upper.rstrip().endswith(" LIMIT"):
        return base
    if " FETCH FIRST " in upper and " ROWS ONLY" in upper:
        return base
    return f"{base} LIMIT {safe_limit}"


def dialect_limit_hint(dialect: str) -> str:
    """人类可读的分页语法提示，用于 repair 文案。"""
    dialect_lower = str(dialect or "clickhouse").lower()
    if "oracle" in dialect_lower:
        return "ROWNUM <= N 或 FETCH FIRST N ROWS ONLY"
    if any(token in dialect_lower for token in ("sqlserver", "mssql", "tsql")):
        return "TOP N"
    return "LIMIT N"
