"""WHERE 条件样例探查诊断单元测试。"""

import pytest

from app.services.ai.where_condition_sample_diagnostic import (
    build_where_condition_probe_repair_hint,
    build_where_format_corrected_sql,
    build_where_sample_probe_plans,
    extract_where_predicate_columns_from_sql,
    format_where_condition_repair_block,
    is_where_condition_sql_error,
    parse_sample_rows,
    rewrite_where_date_literals_as_strings,
    WhereSampleDiagnosticResult,
)

pytestmark = pytest.mark.no_infrastructure


FAILED_SQL = """
SELECT opp.*
FROM VIEW_AI_CULEOPP opp
LEFT JOIN VIEW_AI_CUSTOMER c ON opp.opp_customer_name = c.ID
WHERE (opp.opp_status = 1 OR opp.stage = 4)
  AND opp.CREATE_DATE >= DATE '2026-05-01'
  AND opp.CREATE_DATE < DATE '2026-06-01'
ORDER BY opp.CREATE_DATE DESC
"""


def test_is_where_condition_sql_error_matches_ora01861():
    assert is_where_condition_sql_error("ORA-01861: literal does not match format string")
    assert is_where_condition_sql_error("[TOOL_ERROR] ORA-01722: invalid number")
    assert not is_where_condition_sql_error("unknown column foo")


def test_extract_where_predicate_columns_from_failed_sql():
    refs = extract_where_predicate_columns_from_sql(FAILED_SQL, dialect="oracle")
    columns = {item.column.upper() for item in refs}
    assert "CREATE_DATE" in columns
    assert "OPP_STATUS" in columns or "STAGE" in columns


def test_build_where_sample_probe_plans_oracle():
    plans = build_where_sample_probe_plans(FAILED_SQL, dialect="oracle")
    assert plans
    table, columns, probe_sql = plans[0]
    assert table == "VIEW_AI_CULEOPP"
    assert "CREATE_DATE" in columns
    assert "ROWNUM" in probe_sql.upper()
    assert "CREATE_DATE" in probe_sql.upper()
    assert probe_sql.upper().count("SELECT") >= 2  # 外层 ROWNUM 子查询


def test_build_where_sample_probe_plans_clickhouse():
    plans = build_where_sample_probe_plans(FAILED_SQL, dialect="clickhouse")
    assert plans
    _table, _columns, probe_sql = plans[0]
    assert "LIMIT 5" in probe_sql
    assert "ROWNUM" not in probe_sql.upper()


def test_build_where_condition_probe_repair_hint_includes_probe_sql():
    hint = build_where_condition_probe_repair_hint(FAILED_SQL, dialect="oracle")
    assert "WHERE 条件探查" in hint
    assert "CREATE_DATE" in hint
    assert "```sql" in hint


def test_format_where_condition_repair_block_with_samples():
    block = format_where_condition_repair_block(
        [
            WhereSampleDiagnosticResult(
                table="VIEW_AI_CULEOPP",
                columns=["CREATE_DATE"],
                sample_rows=[{"CREATE_DATE": "2026-05-01 10:00:00"}],
            )
        ]
    )
    assert "平台自动 WHERE 样例探查" in block
    assert "2026-05-01 10:00:00" in block


def test_rewrite_where_date_literals_as_strings():
    sql = (
        "SELECT * FROM VIEW_AI_CULEOPP opp "
        "WHERE opp.CREATE_DATE >= DATE '2026-05-01' AND opp.CREATE_DATE < DATE '2026-06-01'"
    )
    corrected = rewrite_where_date_literals_as_strings(
        sql,
        columns=["CREATE_DATE"],
        sample_values={"create_date": ["2026-05-01 10:00:00"]},
    )
    assert corrected is not None
    assert "DATE '2026-05-01'" not in corrected
    assert "'2026-05-01 00:00:00'" in corrected
    assert "'2026-06-01 00:00:00'" in corrected


def test_build_where_format_corrected_sql_from_diagnostics():
    diagnostics = [
        WhereSampleDiagnosticResult(
            table="VIEW_AI_CULEOPP",
            columns=["CREATE_DATE"],
            sample_rows=[{"CREATE_DATE": "2026-05-01 10:00:00"}],
        )
    ]
    sql = "SELECT * FROM VIEW_AI_CULEOPP opp WHERE opp.CREATE_DATE >= DATE '2026-05-01'"
    corrected = build_where_format_corrected_sql(
        sql,
        diagnostics,
        error_message="ORA-01861: literal does not match format string",
    )
    assert corrected is not None
    assert "DATE '" not in corrected


def test_parse_sample_rows_from_dict_items():
    parsed = {
        "columns": ["CREATE_DATE", "OPP_STATUS"],
        "items": [
            {"CREATE_DATE": "2026-05-01", "OPP_STATUS": "1"},
        ],
    }
    rows = parse_sample_rows(parsed, columns=["CREATE_DATE", "OPP_STATUS"])
    assert rows == [{"CREATE_DATE": "2026-05-01", "OPP_STATUS": "1"}]
