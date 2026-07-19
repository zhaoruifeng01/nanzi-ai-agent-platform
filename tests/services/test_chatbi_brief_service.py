import pytest

from app.services.chatbi_brief_service import (
    UnsupportedBriefClaim,
    build_business_brief,
)


pytestmark = pytest.mark.no_infrastructure


RESULT = {
    "result_id": "result_1",
    "question": "查询本月区域销售额",
    "dataset_name": "sales_ds",
    "rows": {"rows": [{"区域": "华东", "销售额": 120}, {"区域": "华南", "销售额": 80}]},
    "result_summary": "本月区域销售额查询完成",
    "analysis_context": {"time_range": "本月", "metrics": ["销售额"], "dimensions": ["区域"]},
}


def test_business_brief_contains_deterministic_facts_and_evidence_refs():
    brief = build_business_brief(RESULT)
    assert brief["title"] == "本月区域销售额业务简报"
    assert brief["facts"]["row_count"] == 2
    assert brief["facts"]["numeric_summary"]["销售额"]["sum"] == 200.0
    assert brief["evidence"][0]["result_id"] == "result_1"
    assert "核心数据" in brief["markdown"]


def test_business_brief_rejects_claim_without_evidence():
    with pytest.raises(UnsupportedBriefClaim):
        build_business_brief(RESULT, requested_claims=["销售额同比增长 30%"])
