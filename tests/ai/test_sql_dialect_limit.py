"""SQL 方言行数限制 helper 单元测试。"""

import pytest

from app.services.ai.sql_dialect_limit import apply_dialect_row_limit, dialect_limit_hint

pytestmark = pytest.mark.no_infrastructure


def test_oracle_wraps_inner_select_with_rownum():
    sql = apply_dialect_row_limit(
        "SELECT CREATE_DATE FROM VIEW_AI_CULEOPP WHERE CREATE_DATE IS NOT NULL",
        dialect="oracle",
        limit=5,
    )
    assert "ROWNUM <= 5" in sql.upper()
    assert "SELECT CREATE_DATE FROM VIEW_AI_CULEOPP" in sql


def test_mysql_uses_limit():
    sql = apply_dialect_row_limit(
        "SELECT CREATE_DATE FROM t WHERE CREATE_DATE IS NOT NULL",
        dialect="mysql",
        limit=5,
    )
    assert sql.endswith("LIMIT 5")


def test_clickhouse_uses_limit():
    sql = apply_dialect_row_limit(
        "SELECT DISTINCT gxqy FROM zf_view_resroom",
        dialect="clickhouse",
        limit=20,
    )
    assert "LIMIT 20" in sql


def test_sqlserver_uses_top():
    sql = apply_dialect_row_limit(
        "SELECT id FROM hrmresource",
        dialect="sqlserver",
        limit=3,
    )
    assert "SELECT TOP 3" in sql.upper()


def test_dialect_limit_hint():
    assert "ROWNUM" in dialect_limit_hint("oracle_ds")
    assert "TOP" in dialect_limit_hint("mssql_prod")
    assert "LIMIT" in dialect_limit_hint("clickhouse_default")
