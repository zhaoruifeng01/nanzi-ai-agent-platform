import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from sqlalchemy import select, delete

from app.models.task import AgentScheduledTask
from app.services.ai.scheduler_service import scheduler_service
from app.core.orm import AsyncSessionLocal
from app.models.user import User

@pytest.fixture
async def cleanup_tasks():
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AgentScheduledTask))
        await session.commit()

@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """Test start and stop of scheduler."""
    try:
        await scheduler_service.start()
        assert scheduler_service._scheduler.running is True
        
        await scheduler_service.stop()
        assert scheduler_service._scheduler is None
    finally:
        if scheduler_service._scheduler and scheduler_service._scheduler.running:
            await scheduler_service.stop()

@pytest.mark.asyncio
async def test_upsert_and_run_task(seed_data, cleanup_tasks):
    """Test adding a task and manually running it."""
    async with AsyncSessionLocal() as session:
        # Get test user
        res = await session.execute(select(User).where(User.user_name == "test_user"))
        user = res.scalar_one()
        
        # Create a task
        task = AgentScheduledTask(
            name="Test Task",
            user_id=user.id,
            agent_id="test_agent",
            conversation_id="test_conv",
            cron_expr="0 0 * * *", # Daily at midnight
            prompt="Hello world",
            status=1
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        # Start scheduler
        await scheduler_service.start()
        
        try:
            # Sync to scheduler
            await scheduler_service.upsert_task(task)
            
            # Verify it's in scheduler
            job = scheduler_service._scheduler.get_job(f"task_{task.id}")
            assert job is not None
            
            # Mock agent_service
            with patch("app.services.ai.agent_service.agent_service.chat_completion", new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = {"content": "Mocked Response"}
                
                # Run manually
                await scheduler_service.run_task(task.id, is_manual=True)
                
                # Verify mock was called
                mock_chat.assert_called_once()
                args, kwargs = mock_chat.call_args
                assert kwargs["agent_id"] == "test_agent"
                # New behavior adds prefix: 【自动化指令-任务ID: {id}】@test_agent Hello world
                msg_content = kwargs["messages"][0]["content"]
                assert "【自动化指令-任务ID:" in msg_content
                assert "@test_agent Hello world" in msg_content
                assert kwargs["user_info"]["user_id"] == user.id
                
            # Verify DB was updated - use a fresh session to avoid cache
            async with AsyncSessionLocal() as verify_session:
                stmt = select(AgentScheduledTask).where(AgentScheduledTask.id == task.id)
                res = await verify_session.execute(stmt)
                updated_task = res.scalar_one()
                assert updated_task.run_count == 1
                assert updated_task.last_run_at is not None
        finally:
            await scheduler_service.stop()

@pytest.mark.asyncio
async def test_disable_task(seed_data, cleanup_tasks):
    """Test disabling a task removes it from scheduler."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.user_name == "test_user"))
        user = res.scalar_one()
        
        task = AgentScheduledTask(
            name="Disable Test",
            user_id=user.id,
            agent_id="test_agent",
            conversation_id="test_conv_disable",
            cron_expr="0 0 * * *",
            prompt="Bye world",
            status=1
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        await scheduler_service.start()
        try:
            await scheduler_service.upsert_task(task)
            assert scheduler_service._scheduler.get_job(f"task_{task.id}") is not None
            
            # Disable
            task.status = 0
            await scheduler_service.upsert_task(task)
            assert scheduler_service._scheduler.get_job(f"task_{task.id}") is None
            
        finally:
            await scheduler_service.stop()