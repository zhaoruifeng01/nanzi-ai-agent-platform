import sys
import os
import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai.executors.federated_executor import FederatedQueryExecutor, make_markdown_table

pytestmark = pytest.mark.no_infrastructure


def test_parse_federated_plan_robustness():
    # 构造一个测试执行器
    runner = MagicMock()
    runner.user_info = {}
    runner.trace_buffer = []
    
    executor = FederatedQueryExecutor(runner, "", [])
    
    # 1. 测试带 CDATA 包裹的标准格式
    xml_content_1 = """
    <multi_dataset_plan>
      <sub_query dataset_name="energy_usage" temp_table="t_energy">
        <![CDATA[
        SELECT id, power FROM energy WHERE time > '2026-06-01'
        ]]>
      </sub_query>
      <sub_query dataset_name="asset_info" temp_table="t_asset">
        <![CDATA[
        SELECT id, name FROM asset WHERE status = 1
        ]]>
      </sub_query>
      <memory_join>
        <![CDATA[
        SELECT a.name, e.power FROM t_asset a JOIN t_energy e ON a.id = e.id
        ]]>
      </memory_join>
    </multi_dataset_plan>
    """
    
    subs, join_sql = executor._parse_federated_plan(xml_content_1)
    assert len(subs) == 2
    assert subs[0]["dataset_name"] == "energy_usage"
    assert subs[0]["temp_table"] == "t_energy"
    assert "SELECT id, power" in subs[0]["sql"]
    assert subs[1]["dataset_name"] == "asset_info"
    assert subs[1]["temp_table"] == "t_asset"
    assert "SELECT id, name" in subs[1]["sql"]
    assert "SELECT a.name" in join_sql

    # 2. 测试带 HTML 转义的非 CDATA 格式
    xml_content_2 = """
    <multi_dataset_plan>
      <sub_query dataset_name="energy_usage" temp_table="t_energy">
        SELECT id, power FROM energy WHERE time &gt; '2026-06-01'
      </sub_query>
      <memory_join>
        SELECT * FROM t_energy
      </memory_join>
    </multi_dataset_plan>
    """
    subs, join_sql = executor._parse_federated_plan(xml_content_2)
    assert len(subs) == 1
    assert subs[0]["dataset_name"] == "energy_usage"
    assert "time > '2026-06-01'" in subs[0]["sql"]
    assert join_sql == "SELECT * FROM t_energy"


def test_make_markdown_table():
    cols = [{"name": "id"}, {"name": "name"}]
    rows = [[1, "DeviceA"], [2, "DeviceB"]]
    md = make_markdown_table(cols, rows)
    assert "| id | name |" in md
    assert "| --- | --- |" in md
    assert "| 1 | DeviceA |" in md
    assert "| 2 | DeviceB |" in md


def test_federated_memory_join_sql_blocks_external_access():
    assert FederatedQueryExecutor._validate_memory_join_sql("SELECT * FROM t_energy") is None

    error = FederatedQueryExecutor._validate_memory_join_sql("SELECT * FROM read_csv_auto('/etc/passwd')")
    assert error
    assert "外部访问" in error

    error = FederatedQueryExecutor._validate_memory_join_sql("COPY t_energy TO '/tmp/leak.csv'")
    assert error
    assert "只允许" in error or "外部访问" in error


def test_federated_executor_limits_rows_and_maps_duckdb_types():
    rows = [[i] for i in range(1002)]
    limited = FederatedQueryExecutor._limit_rows(rows)

    assert len(limited) == 1000
    assert limited[-1] == [999]
    assert FederatedQueryExecutor._duckdb_type_to_result_type("INTEGER") == "number"
    assert FederatedQueryExecutor._duckdb_type_to_result_type("DOUBLE") == "number"
    assert FederatedQueryExecutor._duckdb_type_to_result_type("BOOLEAN") == "boolean"
    assert FederatedQueryExecutor._duckdb_type_to_result_type("VARCHAR") == "string"


def test_federated_executor_reuses_runner_user_resolvers():
    runner = MagicMock()
    runner.user_info = {"id": "1", "role": "user"}
    runner.trace_buffer = []
    runner._current_user_id.return_value = 42
    runner._current_user_is_admin.return_value = True

    executor = FederatedQueryExecutor(runner, "", [])

    assert executor._current_user_id() == 42
    assert executor._current_user_is_admin() is True


@pytest.mark.asyncio
async def test_cross_dataset_schema_enrichment_filters_unauthorized_targets(monkeypatch):
    from app.services.chatbi_dataset_schema_service import _enrich_with_cross_dataset_schema

    source_table = SimpleNamespace(id=1, physical_name="energy_usage")
    target_dataset = SimpleNamespace(id=2, name="asset_ds", display_name="资产数据", data_source="mysql")
    target_table = SimpleNamespace(
        id=2,
        physical_name="asset_owner",
        dataset_id=2,
        dataset=target_dataset,
        columns=[],
    )

    class FakeScalarResult:
        def all(self):
            return [source_table]

    class FakeExecuteResult:
        def scalars(self):
            return FakeScalarResult()

    class FakeSession:
        async def execute(self, stmt):
            return FakeExecuteResult()

    async def fake_get_cross_dataset_related_tables(session, source_table_ids, **kwargs):
        return [target_table]

    async def fake_config_get(key, default=None):
        return default

    def fake_render_schema(dataset, table, relationships, *, data_source=None):
        return f"dataset: {dataset.name}\ntable_name: {table.physical_name}\ndata_source: {data_source}"

    def fake_format_schema_chunk(index, content):
        return content

    async def deny_permission(self, user_id, resource_type, resource_id):
        return False

    monkeypatch.setattr(
        "app.services.chatbi_dataset_schema_service.MetadataService.get_cross_dataset_related_tables",
        fake_get_cross_dataset_related_tables,
    )
    monkeypatch.setattr(
        "app.services.chatbi_dataset_schema_service.ConfigService.get",
        fake_config_get,
    )
    monkeypatch.setattr(
        "app.services.metadata_rag_service.MetadataRagService.render_table_schema_yaml",
        fake_render_schema,
    )
    monkeypatch.setattr(
        "app.services.schema_chunk_format.format_schema_chunk",
        fake_format_schema_chunk,
    )
    monkeypatch.setattr(
        "app.services.permission_service.PermissionService.check_permission",
        deny_permission,
    )

    schema_text = "dataset: energy_ds\ntable_name: energy_usage\ncolumns:\n  - name: device_id"
    enriched_without_permission = await _enrich_with_cross_dataset_schema(
        FakeSession(),
        schema_text,
        user_id=7,
        is_admin=False,
    )
    assert "asset_owner" not in enriched_without_permission

    async def allow_permission(self, user_id, resource_type, resource_id):
        return resource_type == "metadata" and resource_id == "2"

    monkeypatch.setattr(
        "app.services.permission_service.PermissionService.check_permission",
        allow_permission,
    )
    enriched_with_permission = await _enrich_with_cross_dataset_schema(
        FakeSession(),
        schema_text,
        user_id=7,
        is_admin=False,
    )
    assert "asset_owner" in enriched_with_permission


@pytest.mark.asyncio
async def test_federated_executor_execution():
    # 模拟 Runner 及其环境
    runner = MagicMock()
    runner.user_info = {"id": 1, "role": "user"}
    runner.trace_buffer = MagicMock()
    
    # 模拟 _save_last_data_result_for_followups 行为
    runner._save_last_data_result_for_followups = AsyncMock()
    
    # 模拟 XML 执行计划返回
    mock_llm_response = """
    <multi_dataset_plan>
      <sub_query dataset_name="energy_ds" temp_table="t_energy">
        SELECT device_id, power FROM energy
      </sub_query>
      <sub_query dataset_name="asset_ds" temp_table="t_asset">
        SELECT id, name FROM asset
      </sub_query>
      <memory_join>
        SELECT a.name, e.power FROM t_asset a JOIN t_energy e ON a.id = e.device_id
      </memory_join>
    </multi_dataset_plan>
    """
    
    # Mock LLM Client
    mock_llm_client = MagicMock()
    mock_llm_client.generate_text = AsyncMock(return_value=mock_llm_response)
    
    # Mock LLM Stream Client for synthesis
    mock_llm_stream_client = MagicMock()
    async def mock_stream_messages(*args, **kwargs):
        yield SimpleNamespace(content="根据联邦计算结果，")
        yield SimpleNamespace(content="DeviceA 的能耗为 100。")
    mock_llm_stream_client.stream_messages = mock_stream_messages

    # Mock AgentConfigProvider
    mock_plan_handle = object()
    mock_stream_handle = object()
    async def mock_get_llm(streaming=False, *args, **kwargs):
        return mock_stream_handle if streaming else mock_plan_handle

    def fake_chat_client_from_handle(handle):
        return mock_llm_stream_client if handle is mock_stream_handle else mock_llm_client

    # Mock SQL 执行返回的 JSON 字符串结果
    subquery_1_result = json.dumps({
        "columns": [{"name": "device_id", "type": "str"}, {"name": "power", "type": "int"}],
        "items": [[1, 100], [2, 200]]
    })
    subquery_2_result = json.dumps({
        "columns": [{"name": "id", "type": "str"}, {"name": "name", "type": "str"}],
        "items": [[1, "DeviceA"], [2, "DeviceB"]]
    })
    
    # Mock Metadata
    mock_energy_ds = MagicMock()
    mock_energy_ds.id = 101
    mock_energy_ds.name = "energy_ds"
    mock_energy_ds.data_source = "ck_source"
    
    mock_asset_ds = MagicMock()
    mock_asset_ds.id = 102
    mock_asset_ds.name = "asset_ds"
    mock_asset_ds.data_source = "mysql_source"
    
    # Mock MetadataService
    async def mock_get_dataset_by_name(session, name):
        if name == "energy_ds":
            return mock_energy_ds
        if name == "asset_ds":
            return mock_asset_ds
        return None

    # Mock PermissionService
    async def mock_check_permission(user_id, res_type, res_id):
        # 假设只允许访问 101 和 102
        return res_id in ("101", "102")

    # Mock TraceSpanContext
    mock_span = MagicMock()
    mock_span.set_output = MagicMock()
    
    class FakeTraceSpanContext:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return mock_span
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    executor = FederatedQueryExecutor(runner, "Mock Schema Output", ["energy_ds", "asset_ds"])
    
    with patch("app.services.ai.executors.federated_executor.AgentConfigProvider.get_configured_llm", side_effect=mock_get_llm), \
         patch("app.services.ai.executors.federated_executor.chat_client_from_handle", side_effect=fake_chat_client_from_handle), \
         patch("app.services.ai.executors.federated_executor.AsyncSessionLocal") as mock_session_cls, \
         patch("app.services.permission_service.PermissionService.check_permission", side_effect=mock_check_permission), \
         patch("app.services.metadata_service.MetadataService.get_dataset_by_name", side_effect=mock_get_dataset_by_name), \
         patch("app.services.ai.runtime.agentscope.trace_context.TraceSpanContext", FakeTraceSpanContext), \
         patch("app.services.ai.executors.federated_executor.execute_sql_query_core") as mock_execute_sql:
         
         # Mock execute_sql_query_core 的多次返回
         mock_execute_sql.side_effect = [subquery_1_result, subquery_2_result]
         
         # 准备 Mock session
         mock_session = MagicMock()
         mock_session_cls.return_value.__aenter__.return_value = mock_session
         
         # 执行联邦查询
         generator = executor.execute([], "Mock System Prompt", "查看能耗和资产名称的关联结果")
         
         chunks = []
         async for chunk in generator:
             chunks.append(chunk)
             
         # 校验日志和结果
         logs = [c for c in chunks if c.get("type") == "log"]
         contents = [c for c in chunks if c.get("content") is not None]
         
         success_logs = [log for log in logs if log.get("status") == "success"]

         # 应该有 4 个完成日志：计划生成、2个子查询、Join
         assert len(success_logs) == 4
         assert any(l["title"] == "生成跨源联邦查询计划" and l["status"] == "success" for l in logs)
         assert any("t_energy" in l["details"] and l["status"] == "success" for l in logs)
         assert any("t_asset" in l["details"] and l["status"] == "success" for l in logs)
         assert any(l["title"] == "内存联邦聚合计算" and l["status"] == "success" for l in logs)
         
         # 校验最终输出内容
         full_content = "".join([c["content"] for c in contents])
         assert "DeviceA 的能耗为 100" in full_content
         
         # 校验数据暂存是否成功
         runner._save_last_data_result_for_followups.assert_called_once()
         call_args = runner._save_last_data_result_for_followups.call_args[0]
         assert call_args[0]["sql"] == "SELECT a.name, e.power FROM t_asset a JOIN t_energy e ON a.id = e.device_id"
         assert call_args[0]["data_source"] == "duckdb"
         assert call_args[0]["dataset_name"] == "federated"
         
         # 检查暂存的数据内容
         final_saved_data = call_args[1]
         assert final_saved_data["columns"] == [{"name": "name", "type": "string"}, {"name": "power", "type": "number"}]
         assert final_saved_data["items"] == [["DeviceA", 100], ["DeviceB", 200]]


@pytest.mark.asyncio
async def test_federated_executor_sandboxes_and_closes_duckdb(monkeypatch):
    runner = MagicMock()
    runner.user_info = {"id": 1, "role": "user"}
    runner.trace_buffer = MagicMock()
    runner._save_last_data_result_for_followups = AsyncMock()

    mock_llm_response = """
    <multi_dataset_plan>
      <sub_query dataset_name="energy_ds" temp_table="t_energy">SELECT device_id FROM energy</sub_query>
      <memory_join>SELECT device_id FROM t_energy</memory_join>
    </multi_dataset_plan>
    """
    mock_llm_client = MagicMock()
    mock_llm_client.generate_text = AsyncMock(return_value=mock_llm_response)
    mock_llm_stream_client = MagicMock()

    async def mock_stream_messages(*args, **kwargs):
        yield SimpleNamespace(content="ok")

    mock_llm_stream_client.stream_messages = mock_stream_messages

    async def mock_get_llm(streaming=False, *args, **kwargs):
        return "stream" if streaming else "plan"

    def fake_chat_client_from_handle(handle):
        return mock_llm_stream_client if handle == "stream" else mock_llm_client

    mock_ds = MagicMock()
    mock_ds.id = 101
    mock_ds.name = "energy_ds"
    mock_ds.data_source = "ck_source"

    async def mock_get_dataset_by_name(session, name):
        return mock_ds

    async def mock_check_permission(user_id, res_type, res_id):
        return True

    class FakeTraceSpanContext:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            span = MagicMock()
            span.set_output = MagicMock()
            return span

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    fake_conn = MagicMock()
    fake_res = MagicMock()
    fake_res.fetchall.return_value = [[1]]
    fake_res.description = [("device_id", "INTEGER")]
    fake_conn.execute.return_value = fake_res

    with patch("app.services.ai.executors.federated_executor.AgentConfigProvider.get_configured_llm", side_effect=mock_get_llm), \
         patch("app.services.ai.executors.federated_executor.chat_client_from_handle", side_effect=fake_chat_client_from_handle), \
         patch("app.services.ai.executors.federated_executor.AsyncSessionLocal") as mock_session_cls, \
         patch("app.services.permission_service.PermissionService.check_permission", side_effect=mock_check_permission), \
         patch("app.services.metadata_service.MetadataService.get_dataset_by_name", side_effect=mock_get_dataset_by_name), \
         patch("app.services.ai.runtime.agentscope.trace_context.TraceSpanContext", FakeTraceSpanContext), \
         patch("app.services.ai.executors.federated_executor.duckdb.connect", return_value=fake_conn) as mock_connect, \
         patch("app.services.ai.executors.federated_executor.execute_sql_query_core", AsyncMock(return_value=json.dumps({"columns": [{"name": "device_id"}], "items": [[1]]}))):
        mock_session_cls.return_value.__aenter__.return_value = MagicMock()

        chunks = []
        async for chunk in FederatedQueryExecutor(runner, "", ["energy_ds"]).execute([], "", "test"):
            chunks.append(chunk)

    mock_connect.assert_called_once_with(
        database=":memory:",
        config={"enable_external_access": False},
    )
    fake_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_federated_executor_rejects_dangerous_memory_join_before_execute():
    runner = MagicMock()
    runner.user_info = {"id": 1, "role": "user"}
    runner.trace_buffer = MagicMock()
    runner._save_last_data_result_for_followups = AsyncMock()

    mock_llm_response = """
    <multi_dataset_plan>
      <sub_query dataset_name="energy_ds" temp_table="t_energy">SELECT device_id FROM energy</sub_query>
      <memory_join>SELECT * FROM read_csv_auto('/etc/passwd')</memory_join>
    </multi_dataset_plan>
    """
    mock_llm_client = MagicMock()
    mock_llm_client.generate_text = AsyncMock(return_value=mock_llm_response)

    async def mock_get_llm(streaming=False, *args, **kwargs):
        return "plan"

    def fake_chat_client_from_handle(handle):
        return mock_llm_client

    mock_ds = MagicMock()
    mock_ds.id = 101
    mock_ds.name = "energy_ds"
    mock_ds.data_source = "ck_source"

    async def mock_get_dataset_by_name(session, name):
        return mock_ds

    async def mock_check_permission(user_id, res_type, res_id):
        return True

    class FakeTraceSpanContext:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            span = MagicMock()
            span.set_output = MagicMock()
            return span

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    fake_conn = MagicMock()

    with patch("app.services.ai.executors.federated_executor.AgentConfigProvider.get_configured_llm", side_effect=mock_get_llm), \
         patch("app.services.ai.executors.federated_executor.chat_client_from_handle", side_effect=fake_chat_client_from_handle), \
         patch("app.services.ai.executors.federated_executor.AsyncSessionLocal") as mock_session_cls, \
         patch("app.services.permission_service.PermissionService.check_permission", side_effect=mock_check_permission), \
         patch("app.services.metadata_service.MetadataService.get_dataset_by_name", side_effect=mock_get_dataset_by_name), \
         patch("app.services.ai.runtime.agentscope.trace_context.TraceSpanContext", FakeTraceSpanContext), \
         patch("app.services.ai.executors.federated_executor.duckdb.connect", return_value=fake_conn), \
         patch("app.services.ai.executors.federated_executor.execute_sql_query_core", AsyncMock(return_value=json.dumps({"columns": [{"name": "device_id"}], "items": [[1]]}))):
        mock_session_cls.return_value.__aenter__.return_value = MagicMock()

        chunks = []
        async for chunk in FederatedQueryExecutor(runner, "", ["energy_ds"]).execute([], "", "test"):
            chunks.append(chunk)

    assert any("禁止外部访问" in str(chunk.get("details") or chunk.get("content") or "") for chunk in chunks)
    fake_conn.execute.assert_not_called()
    fake_conn.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
