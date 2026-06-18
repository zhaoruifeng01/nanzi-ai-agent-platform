import pytest

from app.services.ai.chatbi_sql_user_messages import (
    GENERIC_SQL_ERROR_CONTENT,
    map_sql_tool_error_for_user,
)

pytestmark = pytest.mark.no_infrastructure


@pytest.mark.parametrize(
    ("raw", "title_substr", "content_substr"),
    [
        (
            "[Permission Denied] zhangsan(1) 无权访问表 'ods_order'",
            "无权访问",
            "ods_order",
        ),
        (
            "[Permission Denied] 无法校验表权限：缺少用户身份",
            "无法校验",
            "身份",
        ),
        (
            "Error: Dataset 'sales_dw' not found. Please verify the dataset name.",
            "数据集不存在",
            "sales_dw",
        ),
        (
            "[Validation Failed] 表 't_x' 不属于当前指定的数据集 'order_ds'，严禁跨数据集或凭空猜表。",
            "不匹配",
            "t_x",
        ),
        (
            "[Validation Failed] '订单' 是业务术语，并非物理表名，不能直接用于 SQL。请改用 get_dataset_schema 返回的物理表名 'ods_order'。",
            "物理表名",
            "订单",
        ),
        (
            "[Validation Failed] user(2)物理表 'ghost_tbl' 未在元数据中注册或不存在。",
            "不存在",
            "ghost_tbl",
        ),
        (
            "[Security Error] Failed to apply data permissions: boom",
            "数据权限",
            "行级",
        ),
    ],
)
def test_map_sql_tool_error_for_user_specific_cases(raw, title_substr, content_substr):
    presentation = map_sql_tool_error_for_user(raw)
    assert presentation.specific is True
    assert title_substr in presentation.title
    assert content_substr in presentation.content
    assert "[Permission Denied]" not in presentation.content
    assert "[Validation Failed]" not in presentation.content


def test_map_sql_tool_error_for_user_preserves_raw_for_repair_is_separate():
    raw = "[Validation Failed] 表 't_x' 不属于当前指定的数据集 'order_ds'，严禁跨数据集或凭空猜表。"
    presentation = map_sql_tool_error_for_user(raw)
    assert raw != presentation.content
    assert "order_ds" in presentation.content


def test_map_sql_tool_error_for_user_generic_fallback():
    presentation = map_sql_tool_error_for_user("some opaque upstream failure")
    assert presentation.specific is False
    assert presentation.content == GENERIC_SQL_ERROR_CONTENT
