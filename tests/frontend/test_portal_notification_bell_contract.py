from pathlib import Path

import pytest


pytestmark = pytest.mark.no_infrastructure
ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_mounts_persistent_notification_bell():
    dashboard = (ROOT / "frontend/src/views/Dashboard.vue").read_text(encoding="utf-8")
    bell = (ROOT / "frontend/src/components/PortalNotificationBell.vue").read_text(encoding="utf-8")
    assert "PortalNotificationBell" in dashboard
    assert "/api/portal/inbox/unread-count" in bell
    assert "/api/portal/inbox/read-all" in bell
    assert "全部已读" in bell
    assert "关闭通知" in bell
    assert '@mouseleave="scheduleClose"' in bell
    assert '@mouseenter="cancelScheduledClose"' in bell
    assert "report_id" in bell and "resource_id" in bell


def test_manual_saved_report_runs_follow_notification_policy():
    scheduler = (ROOT / "app/services/ai/scheduler_service.py").read_text(encoding="utf-8")
    endpoint = (ROOT / "app/api/portal/endpoints/saved_reports.py").read_text(encoding="utf-8")
    assert 'trigger_label = "手动触发" if is_manual else "定时触发"' in scheduler
    assert "if subscription.notify_on_success:" in scheduler
    assert "if not is_manual and subscription.notify_on_success" not in scheduler
    assert "_saved_report_subscription_wrapper(row.id, is_manual=True)" in endpoint


def test_notification_bell_uses_visibility_aware_polling_and_manual_refresh():
    bell = (ROOT / "frontend/src/components/PortalNotificationBell.vue").read_text(encoding="utf-8")

    assert "60_000" in bell
    assert "30_000" in bell
    assert 'document.addEventListener("visibilitychange"' in bell
    assert 'window.addEventListener("focus"' in bell
    assert "document.hidden" in bell
    assert "refreshNotifications" in bell
    assert 'aria-label="刷新消息"' in bell
    assert "刷新中" in bell


def test_notification_bell_supports_single_delete_and_clear_read_with_confirmation():
    bell = (ROOT / "frontend/src/components/PortalNotificationBell.vue").read_text(encoding="utf-8")

    for text in ("删除消息", "清空已读", "确认删除这条消息", "确认清空已读消息", "confirmDeleteNotifications"):
        assert text in bell
    assert 'axios.delete(`/api/portal/inbox/${deleteTarget.value.id}`)' in bell
    assert 'axios.delete("/api/portal/inbox/read")' in bell


def test_notification_header_uses_two_rows_on_narrow_panels():
    bell = (ROOT / "frontend/src/components/PortalNotificationBell.vue").read_text(encoding="utf-8")

    assert "notification-header-main" in bell
    assert "notification-header-actions" in bell
    assert "whitespace-nowrap" in bell
