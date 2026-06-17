"""
ChatBI 数据集 Schema 获取：与工具 `get_dataset_schema` 共用逻辑，供 HTTP 等调用复用。
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.services.config_service import ConfigService
from app.services.metadata_service import MetadataService
from app.services.schema_chunk_format import format_schema_chunk, format_schema_hits

logger = logging.getLogger(__name__)


async def fetch_dataset_schema_core(
    session: AsyncSession,
    *,
    keywords: Optional[str] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    api_key: Optional[str] = None,
) -> str:
    """
    按当前用户权限获取数据集 Schema 文本（local/ragflow 均优先返回检索片段）。

    Args:
        keywords: 元数据检索 query；local 模式下用于本地向量检索，向量异常时用于 MySQL LIKE 兜底。
        user_id: 用户 ID；可与 api_key 二选一补全（工具场景）。
        is_admin: 是否平台管理员。
        api_key: 无 user_id 时用于解析用户身份。
    """
    try:
        return await _fetch_dataset_schema_impl(
            session,
            keywords=keywords,
            user_id=user_id,
            is_admin=is_admin,
            api_key=api_key,
        )
    except Exception as e:
        logger.error("[fetch_dataset_schema_core] Schema retrieval failed: %s", e, exc_info=True)
        return f"[Tool Error] Failed to retrieve metadata: {str(e)}"


async def _format_fallback_dataset_chunks(session: AsyncSession, dataset_id: int, start_index: int) -> tuple[list[str], int]:
    """MySQL 兜底：导出与向量索引一致的单表/指标 YAML 块。"""
    raw_chunks = await MetadataService.build_dataset_schema_chunk_contents(session, dataset_id)
    formatted: list[str] = []
    index = start_index
    for content in raw_chunks:
        piece = format_schema_chunk(index, content)
        if piece:
            formatted.append(piece)
            index += 1
    return formatted, index


async def _fetch_dataset_schema_impl(
    session: AsyncSession,
    *,
    keywords: Optional[str] = None,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    api_key: Optional[str] = None,
) -> str:
    user_id_eff = user_id
    is_admin_eff = bool(is_admin)

    if user_id_eff is None and api_key:
        u_info = await AuthService.verify_api_key(api_key, session)
        if u_info:
            user_id_eff = int(u_info["user_id"])
            if u_info.get("role") == "admin":
                is_admin_eff = True

    authorized_datasets = await MetadataService.search_datasets(
        session,
        query=None,
        user_id=user_id_eff,
        is_admin=is_admin_eff,
        status=1,
    )

    if not authorized_datasets:
        return "No authorized datasets found. You do not have permission to view any data."

    provider = await ConfigService.get("metadata_provider", default="local")
    logger.info("[fetch_dataset_schema_core] provider=%s", str(provider).upper())

    # --- RAGFlow Mode ---
    if provider == "ragflow":
        from app.services.ai.ragflow_client import RagFlowClient
        from app.services.metadata_rag_service import MetadataRagService, MetadataServiceUnavailableError

        rag_ids = [ds.rag_dataset_id for ds in authorized_datasets if ds.rag_dataset_id]

        if not rag_ids:
            return "Authorized datasets found, but none are synced to RAG knowledge base."

        # If no keywords provided, return a directory of datasets instead of searching
        if not keywords:
            directory = ["Available Datasets (Please provide keywords to search specific tables):"]
            for ds in authorized_datasets:
                if ds.rag_dataset_id:
                    directory.append(f"- {ds.display_name or ds.name} (Source: {ds.data_source or 'clickhouse'})")
                    if ds.description:
                        directory.append(f"  Description: {ds.description}")
            return "\n".join(directory)

        query = keywords
        threshold = float(await ConfigService.get("ragflow_similarity_threshold") or 0.2)
        weight = float(await ConfigService.get("ragflow_vector_weight") or 0.3)
        top_k = int(await ConfigService.get("ragflow_metadata_top_k") or 5)

        logger.info(
            "[fetch_dataset_schema_core] ragflow top_k=%s threshold=%s weight=%s",
            top_k,
            threshold,
            weight,
        )

        client = RagFlowClient()
        try:
            chunks, trace_logs = await MetadataRagService.retrieve_with_retry(
                client,
                query,
                rag_ids,
                top_k=top_k,
                threshold=threshold,
                weight=weight,
            )
        except MetadataServiceUnavailableError as e:
            logger.error("[fetch_dataset_schema_core] Metadata service unavailable: %s", e)
            return MetadataRagService.unavailable_hint(str(e))

        if not chunks:
            return f"No relevant schema info found for '{query}'.\nDebug Logs: {'; '.join(trace_logs)}"

        filtered_hits = []
        for chunk in chunks:
            try:
                similarity = float(chunk.get("similarity", 0.0) or 0.0)
            except (TypeError, ValueError):
                similarity = 0.0
            if similarity < threshold:
                continue
            content = str(chunk.get("content") or "").strip()
            if not content:
                continue
            filtered_hits.append({
                "content": content,
                "similarity": similarity,
                "doc_name": chunk.get("doc_name", "unknown"),
            })

        if filtered_hits:
            return format_schema_hits(filtered_hits)
        return f"No relevant schema info found for '{query}'.\nDebug Logs: {'; '.join(trace_logs)}"

    # --- Local Mode (Default) ---
    query = (keywords or "").strip()
    threshold = float(await ConfigService.get("ragflow_similarity_threshold") or 0.2)
    top_k = int(await ConfigService.get("ragflow_metadata_top_k") or 5)

    if query:
        try:
            from app.services.ai.embedding_client import EmbeddingClient
            from app.services.ai.metadata_index_service import MetadataIndexService

            authorized_ids = None if is_admin_eff else [
                ds.id for ds in authorized_datasets if getattr(ds, "id", None) is not None
            ]
            query_embedding = await EmbeddingClient.embed_text(query, use_global=True)
            redis_results = await MetadataIndexService.search_knn(
                query_embedding=query_embedding,
                authorized_dataset_ids=authorized_ids,
                top_k=top_k,
            )

            filtered_hits = []
            for item in redis_results:
                try:
                    similarity = float(item.get("similarity", 0.0) or 0.0)
                except (TypeError, ValueError):
                    similarity = 0.0
                if similarity < threshold:
                    continue
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                filtered_hits.append({
                    "content": content,
                    "similarity": similarity,
                    "doc_name": item.get("doc_name", "unknown"),
                })

            if filtered_hits:
                return format_schema_hits(filtered_hits)
            return (
                f"No relevant schema info found for '{query}'.\n"
                f"Debug Logs: Redis Vector Search completed. Found {len(redis_results)} raw items; "
                f"no hit above threshold {threshold}"
            )
        except Exception as ex:
            logger.warning(
                "[fetch_dataset_schema_core] Local Redis vector search failed: %s. Falling back to MySQL keyword search.",
                ex,
            )

    if not query:
        return "No relevant schema info found for ''.\nDebug Logs: local metadata query is empty"

    found_datasets = await MetadataService.search_datasets(
        session,
        query=query,
        user_id=user_id_eff,
        is_admin=is_admin_eff,
        status=1,
    )
    if not found_datasets:
        return f"No relevant schema info found for '{query}'.\nDebug Logs: local MySQL keyword search returned 0 datasets"

    results: list[str] = []
    next_index = 1
    for ds in found_datasets:
        chunks, next_index = await _format_fallback_dataset_chunks(session, ds.id, next_index)
        results.extend(chunks)

    return "\n\n".join(results)
