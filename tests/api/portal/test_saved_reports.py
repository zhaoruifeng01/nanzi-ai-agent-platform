import json
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.portal.endpoints import saved_reports

pytestmark = pytest.mark.no_infrastructure


def test_saved_report_static_sql_stays_compatible():
    report = saved_reports.SavedReportItem.model_validate(
        {
            "id": "rpt_1",
            "title": "固定报表",
            "sql_content": "SELECT * FROM orders WHERE created_at >= '2026-06-01'",
            "dataset_id": None,
            "data_source": "mysql_test",
            "original_query": "查订单",
            "created_at": "2026-06-27T00:00:00+00:00",
        }
    )

    sql, params = saved_reports._resolve_report_sql(
        report,
        body=saved_reports.ExecuteReportRequest.model_validate({}),
        today=date(2026, 6, 27),
    )

    assert sql == "SELECT * FROM orders WHERE created_at >= '2026-06-01'"
    assert params == {}
    assert report.mode == "static_sql"
    assert report.analysis_mode == "manual"


def test_saved_report_detects_two_date_literals_as_default_date_range_template():
    report = saved_reports._build_saved_report_item(
        report_id="rpt_2",
        title="订单月报",
        sql_clean="SELECT * FROM orders WHERE created_at >= '2026-06-01' AND created_at < '2026-07-01'",
        dataset_id=3,
        data_source="mysql_test",
        original_query="本月订单",
        created_at="2026-06-27T00:00:00+00:00",
        body=saved_reports.SaveReportRequest.model_validate(
            {
                "title": "订单月报",
                "sql_content": "SELECT * FROM orders WHERE created_at >= '2026-06-01' AND created_at < '2026-07-01'",
                "data_source": "mysql_test",
                "analysis_mode": "auto",
            }
        ),
    )

    assert report.mode == "param_sql"
    assert report.sql_template == "SELECT * FROM orders WHERE created_at >= {{start_date}} AND created_at < {{end_date}}"
    assert report.default_params["date_range"] == "month_start_to_today"
    assert report.analysis_mode == "auto"


def test_saved_report_param_sql_renders_builtin_last_7_days():
    report = saved_reports.SavedReportItem.model_validate(
        {
            "id": "rpt_3",
            "title": "近七天订单",
            "sql_content": "SELECT * FROM orders",
            "sql_template": "SELECT * FROM orders WHERE created_at >= {{start_date}} AND created_at < {{end_date}}",
            "mode": "param_sql",
            "params_schema": [
                {"name": "date_range", "type": "date_range", "label": "日期范围", "default": "last_7_days"}
            ],
            "default_params": {"date_range": "last_7_days"},
            "data_source": "mysql_test",
            "dataset_id": None,
            "original_query": "近七天订单",
            "created_at": "2026-06-27T00:00:00+00:00",
            "analysis_mode": "auto",
        }
    )

    sql, params = saved_reports._resolve_report_sql(
        report,
        body=saved_reports.ExecuteReportRequest.model_validate({}),
        today=date(2026, 6, 27),
    )

    assert sql == "SELECT * FROM orders WHERE created_at >= '2026-06-21' AND created_at < '2026-06-28'"
    assert params == {"start_date": "2026-06-21", "end_date": "2026-06-28", "date_range": "last_7_days"}


def test_saved_report_param_sql_rejects_unknown_placeholder():
    report = saved_reports.SavedReportItem.model_validate(
        {
            "id": "rpt_4",
            "title": "非法模板",
            "sql_content": "SELECT * FROM orders",
            "sql_template": "SELECT * FROM orders WHERE tenant_id = {{tenant_id}}",
            "mode": "param_sql",
            "params_schema": [{"name": "date_range", "type": "date_range", "label": "日期范围"}],
            "default_params": {"date_range": "today"},
            "data_source": "mysql_test",
            "dataset_id": None,
            "original_query": "订单",
            "created_at": "2026-06-27T00:00:00+00:00",
        }
    )

    with pytest.raises(saved_reports.ReportParameterError, match="不允许的报表参数"):
        saved_reports._resolve_report_sql(
            report,
            body=saved_reports.ExecuteReportRequest.model_validate({}),
            today=date(2026, 6, 27),
        )


@pytest.mark.asyncio
async def test_execute_saved_report_uses_rendered_sql_and_enables_table_auth(monkeypatch):
    redis = AsyncMock()
    redis.hget = AsyncMock(
        return_value=json.dumps(
            {
                "id": "rpt_5",
                "title": "动态月报",
                "sql_content": "SELECT * FROM orders",
                "sql_template": "SELECT * FROM orders WHERE created_at >= {{start_date}} AND created_at < {{end_date}}",
                "mode": "param_sql",
                "params_schema": [{"name": "date_range", "type": "date_range", "label": "日期范围"}],
                "default_params": {"date_range": "month_start_to_today"},
                "data_source": "mysql_test",
                "dataset_id": None,
                "original_query": "本月订单",
                "created_at": "2026-06-27T00:00:00+00:00",
                "analysis_mode": "auto",
            }
        )
    )
    captured = {}

    async def fake_execute_sql_query_core(*args, **kwargs):
        captured.update(kwargs)
        return json.dumps({"items": [{"orders": 3}]})

    monkeypatch.setattr(saved_reports, "get_redis", AsyncMock(return_value=redis))
    monkeypatch.setattr(saved_reports, "execute_sql_query_core", fake_execute_sql_query_core)

    response = await saved_reports.execute_saved_report(
        "rpt_5",
        body=saved_reports.ExecuteReportRequest.model_validate({"params": {"date_range": "today"}}),
        conversation_id=None,
        user_info={"user_id": "7", "role": "user", "user_name": "alice"},
        db=AsyncMock(),
    )

    assert response.data == {"items": [{"orders": 3}]}
    assert captured["sql"] == "SELECT * FROM orders WHERE created_at >= '2026-06-27' AND created_at < '2026-06-28'"
    assert captured["bypass_table_auth"] is False


@pytest.mark.asyncio
async def test_update_saved_report_rebuilds_parameter_template(monkeypatch):
    original = {
        "id": "rpt_edit",
        "title": "旧标题",
        "sql_content": "SELECT * FROM orders WHERE created_at >= '2026-05-01'",
        "data_source": "mysql_test",
        "dataset_id": None,
        "original_query": "订单",
        "created_at": "2026-06-27T00:00:00+00:00",
    }
    redis = AsyncMock()
    redis.hget = AsyncMock(return_value=json.dumps(original))
    redis.hset = AsyncMock()
    monkeypatch.setattr(saved_reports, "get_redis", AsyncMock(return_value=redis))

    async def fake_execute_sql_query_core(*args, **kwargs):
        assert kwargs["auth_check_only"] is True
        assert kwargs["bypass_table_auth"] is False
        return json.dumps({"allowed": True})

    monkeypatch.setattr(saved_reports, "execute_sql_query_core", fake_execute_sql_query_core)

    response = await saved_reports.update_saved_report(
        "rpt_edit",
        body=saved_reports.UpdateReportRequest.model_validate(
            {
                "title": "本月订单",
                "sql_content": "SELECT * FROM orders WHERE created_at >= '2026-06-01' AND created_at < '2026-07-01'",
                "data_source": "mysql_test",
                "analysis_mode": "auto",
            }
        ),
        user_info={"user_id": "7", "role": "user"},
        db=AsyncMock(),
    )

    updated = response.data
    assert updated.id == "rpt_edit"
    assert updated.title == "本月订单"
    assert updated.created_at == original["created_at"]
    assert updated.mode == "param_sql"
    assert updated.sql_template == "SELECT * FROM orders WHERE created_at >= {{start_date}} AND created_at < {{end_date}}"
    assert updated.analysis_mode == "auto"
    redis.hset.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_saved_report_rejects_unauthorized_table_before_saving(monkeypatch):
    original = {
        "id": "rpt_edit",
        "title": "旧标题",
        "sql_content": "SELECT * FROM orders",
        "data_source": "mysql_test",
        "dataset_id": None,
        "original_query": "订单",
        "created_at": "2026-06-27T00:00:00+00:00",
    }
    redis = AsyncMock()
    redis.hget = AsyncMock(return_value=json.dumps(original))
    redis.hset = AsyncMock()
    monkeypatch.setattr(saved_reports, "get_redis", AsyncMock(return_value=redis))

    async def fake_execute_sql_query_core(*args, **kwargs):
        assert kwargs["sql"] == "SELECT * FROM secret_orders"
        assert kwargs["auth_check_only"] is True
        assert kwargs["dry_run"] is False
        assert kwargs["bypass_table_auth"] is False
        return "[Permission Denied] alice(7) 无权访问表 'secret_orders'"

    monkeypatch.setattr(saved_reports, "execute_sql_query_core", fake_execute_sql_query_core)

    with pytest.raises(HTTPException) as exc_info:
        await saved_reports.update_saved_report(
            "rpt_edit",
            body=saved_reports.UpdateReportRequest.model_validate(
                {
                    "title": "越权报表",
                    "sql_content": "SELECT * FROM secret_orders",
                    "data_source": "mysql_test",
                }
            ),
            user_info={"user_id": "7", "role": "user", "user_name": "alice"},
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 400
    assert "无权访问表" in exc_info.value.detail
    redis.hset.assert_not_awaited()
