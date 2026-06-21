import pytest
import json
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai.sql_sandbox_gate import SQLSandboxGate, SQLSandboxResult

@pytest.mark.asyncio
async def test_sql_sandbox_join_cross_blocked():
    """
    测试用例 1: 验证无条件 JOIN (如 CROSS JOIN 或普通 JOIN 但缺失 ON/USING 条件) 会被沙箱拦截。
    """
    mock_session = AsyncMock(spec=AsyncSession)
    
    # 场景 A: 显式 CROSS JOIN
    sql_cross = "SELECT a.id, b.name FROM table_a a CROSS JOIN table_b b"
    res_cross = await SQLSandboxGate.verify_and_optimize(
        session=mock_session,
        sql=sql_cross,
        data_source="clickhouse_test",
        dialect="clickhouse"
    )
    assert res_cross.allowed is False
    assert "CROSS JOIN 笛卡尔积操作" in res_cross.message
    
    # 场景 B: 显式 JOIN 但无 ON/USING
    sql_no_cond = "SELECT * FROM table_a JOIN table_b"
    res_no_cond = await SQLSandboxGate.verify_and_optimize(
        session=mock_session,
        sql=sql_no_cond,
        data_source="clickhouse_test",
        dialect="clickhouse"
    )
    assert res_no_cond.allowed is False
    assert "包含没有关联条件的 JOIN 操作" in res_no_cond.message

    # 场景 C: 显式 LEFT JOIN 但带了 ON
    # 应该被放行（即使没有 explain 也会被放行，除非 explain 超过限制）
    sql_valid_join = "SELECT * FROM table_a a LEFT JOIN table_b b ON a.id = b.id"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = "[]"  # 模拟空 Explain 返回
        res_valid = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_valid_join,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res_valid.allowed is True
        assert "LIMIT 500" in res_valid.optimized_sql  # 因为没有聚合，没有 LIMIT，所以被自动注入 LIMIT 500

@pytest.mark.asyncio
async def test_sql_sandbox_auto_inject_limit():
    """
    测试用例 2: 验证无 LIMIT 的明细 SELECT 会被沙箱网关自动追加 LIMIT 500 限制。
    """
    mock_session = AsyncMock(spec=AsyncSession)
    
    # 场景 A: 纯明细查询无 LIMIT
    sql_plain = "SELECT id, name, val FROM my_table WHERE val > 10"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        # Mock ClickHouse Explain 返回，假装扫描了很少行
        mock_api.return_value = json.dumps([{"Explain": "Read 100 rows"}])
        
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_plain,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res.allowed is True
        assert "LIMIT 500" in res.optimized_sql

    # 场景 B: 带有 LIMIT，不应该被注入
    sql_with_limit = "SELECT id, name, val FROM my_table WHERE val > 10 LIMIT 50"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = json.dumps([{"Explain": "Read 50 rows"}])
        
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_with_limit,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res.allowed is True
        assert "LIMIT 500" not in res.optimized_sql
        assert "LIMIT 50" in res.optimized_sql

    # 场景 C: 带有 GROUP BY 聚合函数，不应该被注入 LIMIT 500
    sql_agg = "SELECT name, SUM(val) FROM my_table GROUP BY name"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = json.dumps([{"Explain": "Read 200 rows"}])
        
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_agg,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res.allowed is True
        assert "LIMIT" not in res.optimized_sql

    # 场景 D: Oracle 方言已带有 ROWNUM 限制，不应追加 LIMIT/FETCH FIRST
    sql_oracle_rownum = "SELECT * FROM my_table WHERE ROWNUM <= 100"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = json.dumps([{"rows": "100"}])
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_oracle_rownum,
            data_source="oracle_test",
            dialect="oracle"
        )
        assert res.allowed is True
        assert "FETCH FIRST" not in res.optimized_sql
        assert "LIMIT" not in res.optimized_sql

    # 场景 E: Oracle 方言已带有 FETCH FIRST 限制，不应追加 LIMIT/FETCH FIRST
    sql_oracle_fetch = "SELECT * FROM my_table FETCH FIRST 50 ROWS ONLY"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = json.dumps([{"rows": "50"}])
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_oracle_fetch,
            data_source="oracle_test",
            dialect="oracle"
        )
        assert res.allowed is True
        assert "FETCH FIRST 500" not in res.optimized_sql

@pytest.mark.asyncio
async def test_sql_sandbox_explain_rows_blocked():
    """
    测试用例 3: 验证大表全表扫描 Explain 预估超限时的阻断熔断提示。
    """
    mock_session = AsyncMock(spec=AsyncSession)
    
    # 场景 A: 估算扫描行数 600 万行（超限 500 万行）
    sql_large = "SELECT * FROM huge_table"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        # Mock ClickHouse Explain 返回，扫描 6,000,000 行
        mock_api.return_value = json.dumps([{"Explain": "Read 6000000 rows"}])
        
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_large,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res.allowed is False
        assert "物理执行计划预估扫描行数为 6,000,000 行" in res.message
        assert "已超过系统安全上限" in res.message

    # 场景 B: 估算扫描行数 400 万行（安全范围内，放行，但自动注入 limit）
    sql_safe = "SELECT * FROM huge_table"
    with patch("app.services.ai.sql_sandbox_gate.call_external_sql_api", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = json.dumps([{"Explain": "Read 4000000 rows"}])
        
        res = await SQLSandboxGate.verify_and_optimize(
            session=mock_session,
            sql=sql_safe,
            data_source="clickhouse_test",
            dialect="clickhouse"
        )
        assert res.allowed is True
        assert "LIMIT 500" in res.optimized_sql
