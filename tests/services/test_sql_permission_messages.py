from unittest.mock import AsyncMock

import pytest

from app.services import sql_query_execution_service as sql_service


@pytest.mark.asyncio
@pytest.mark.no_infrastructure
async def test_table_permission_denied_message_includes_user_identity(monkeypatch):
    async def fake_allowed(_session, _user_id):
        return set()

    async def fake_registered(_session):
        return {"ck_fact_donghuan_real_metric_hbase"}

    monkeypatch.setattr(sql_service, "_fetch_allowed_physical_lowers_for_user", fake_allowed)
    monkeypatch.setattr(sql_service, "_fetch_all_registered_physical_lowers", fake_registered)

    result = await sql_service.enforce_physical_table_permissions_for_select(
        AsyncMock(),
        sql="SELECT * FROM ck_fact_donghuan_real_metric_hbase",
        dialect="clickhouse",
        user_id_eff=4,
        is_admin_eff=False,
        user_identity_label="chenxiaolong(4)",
    )

    assert result == "[Permission Denied] chenxiaolong(4) 无权访问表 'ck_fact_donghuan_real_metric_hbase'"
