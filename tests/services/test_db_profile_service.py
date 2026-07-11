import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.db_connection import DbProfileTask
from app.services.db_profile_service import (
    DbProfileService,
    TASK_STATUS_RUNNING,
    TASK_STATUS_CANCELLED,
    STALE_TASK_MINUTES,
)


def test_extract_result_rows_prefers_rows_then_items():
    assert DbProfileService._extract_result_rows({"rows": [[1]], "items": [[2]]}) == [[1]]
    assert DbProfileService._extract_result_rows({"items": [[2]]}) == [[2]]
    assert DbProfileService._extract_result_rows({}) == []


def test_extract_column_names_from_dict_columns():
    cols = [{"name": "ID", "type": "NUMBER"}, {"name": "NAME", "type": "VARCHAR2"}]
    assert DbProfileService._extract_column_names(cols) == ["ID", "NAME"]


def test_sanitize_sample_value_truncates_long_strings():
    long_text = "x" * 200
    result = DbProfileService._sanitize_sample_value(long_text)
    assert result.endswith("...")
    assert len(result) == 153


def test_truncate_ddl():
    ddl = "A" * 70000
    truncated = DbProfileService._truncate_ddl(ddl)
    assert len(truncated) < len(ddl)
    assert "truncated" in truncated


def test_post_process_scores_penalizes_empty_samples():
    score, temp, reason, ignored = DbProfileService._post_process_scores(
        {"confidence_score": 90, "is_temporary": False, "confidence_reason": "ok"},
        "[]",
        "orders",
    )
    assert score == 60
    assert "样例数据为空" in reason


def test_post_process_scores_penalizes_temp_table_names():
    score, temp, reason, ignored = DbProfileService._post_process_scores(
        {"confidence_score": 90, "is_temporary": False, "confidence_reason": ""},
        json.dumps([{"id": 1}]),
        "tmp_orders",
    )
    assert temp == 1
    assert score == 50
    assert ignored == 1


def test_is_task_stale():
    fresh = DbProfileTask(
        connection_id=1,
        status=TASK_STATUS_RUNNING,
        total_tables=10,
        processed_tables=1,
        updated_at=datetime.now(),
    )
    stale = DbProfileTask(
        connection_id=1,
        status=TASK_STATUS_RUNNING,
        total_tables=10,
        processed_tables=1,
        updated_at=datetime.now() - timedelta(minutes=STALE_TASK_MINUTES + 1),
    )
    assert DbProfileService._is_task_stale(fresh) is False
    assert DbProfileService._is_task_stale(stale) is True


@pytest.mark.asyncio
async def test_fetch_sample_data_builds_json():
    adapter = AsyncMock()
    adapter.execute_sql.return_value = {
        "columns": [{"name": "ID", "type": "int"}],
        "items": [[1], [2]],
    }
    result = await DbProfileService._fetch_sample_data(adapter, "mysql", "orders")
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0]["ID"] == 1


@pytest.mark.asyncio
async def test_should_stop_when_task_cancelled():
    cancelled_task = MagicMock()
    cancelled_task.status = TASK_STATUS_CANCELLED

    with patch.object(DbProfileService, "get_task_status", AsyncMock(return_value=cancelled_task)):
        assert await DbProfileService._should_stop_profiling(1) is True


def test_normalize_page_clamps_values():
    page, size = DbProfileService._normalize_page(0, 9999)
    assert page == 1
    assert size == 200
    page, size = DbProfileService._normalize_page(3, 50)
    assert page == 3
    assert size == 50
