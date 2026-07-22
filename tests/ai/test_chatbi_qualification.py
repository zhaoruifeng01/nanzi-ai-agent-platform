from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai.chatbi_qualification import (
    ChatBIMode,
    DatasetCandidate,
    qualify_chatbi_request,
)


pytestmark = pytest.mark.no_infrastructure


def test_action_word_does_not_qualify_machine_file_aggregation_for_chatbi():
    result = qualify_chatbi_request(
        domain="local_file",
        operation="aggregate",
        dataset_candidates=[],
    )

    assert result.mode == ChatBIMode.DENY
    assert result.evidence_level == "source_conflict"


def test_authorized_dataset_candidate_directly_qualifies_chatbi():
    result = qualify_chatbi_request(
        domain="chatbi_business_data",
        operation="aggregate",
        dataset_candidates=[
            DatasetCandidate(
                dataset_id=12,
                display_name="订单分析",
                similarity=0.82,
                content="订单、客户、销售金额与区域趋势",
            )
        ],
    )

    assert result.mode == ChatBIMode.DIRECT
    assert result.evidence_level == "dataset_match"
    assert result.matched_dataset_ids == (12,)


def test_business_domain_without_dataset_match_only_allows_clarification():
    result = qualify_chatbi_request(
        domain="chatbi_business_data",
        operation="aggregate",
        dataset_candidates=[],
    )

    assert result.mode == ChatBIMode.CLARIFY
    assert result.evidence_level == "semantic_only"


def test_previous_chatbi_result_is_direct_evidence_for_visualization():
    result = qualify_chatbi_request(
        domain="conversation_context",
        operation="visualize",
        dataset_candidates=[],
        previous_chatbi_result=True,
    )

    assert result.mode == ChatBIMode.DIRECT
    assert result.evidence_level == "previous_chatbi_result"


@pytest.mark.asyncio
async def test_authorized_dataset_candidates_are_scoped_before_vector_search():
    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch(
        "app.core.orm.AsyncSessionLocal",
        return_value=_SessionContext(),
    ), patch(
        "app.services.metadata_service.MetadataService.search_datasets",
        new_callable=AsyncMock,
        return_value=[SimpleNamespace(id=12, name="orders", display_name="订单分析")],
    ) as search_datasets, patch(
        "app.services.ai.embedding_client.EmbeddingClient.embed_text",
        new_callable=AsyncMock,
        return_value=[0.1, 0.2],
    ), patch(
        "app.services.ai.metadata_index_service.MetadataIndexService.search_knn",
        new_callable=AsyncMock,
        return_value=[
            {
                "dataset_id": 12,
                "doc_name": "orders.txt",
                "content": "订单金额与客户区域",
                "similarity": 0.81,
            }
        ],
    ) as search_knn:
        from app.services.ai.chatbi_qualification import resolve_authorized_dataset_candidates

        candidates = await resolve_authorized_dataset_candidates(
            "统计订单金额",
            user_id=7,
        )

    assert candidates[0].dataset_id == 12
    assert candidates[0].display_name == "订单分析"
    assert candidates[0].similarity == 0.81
    search_datasets.assert_awaited_once()
    search_knn.assert_awaited_once_with(
        query_embedding=[0.1, 0.2],
        authorized_dataset_ids=[12],
        top_k=3,
    )
