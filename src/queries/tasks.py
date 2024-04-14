import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from models import Task, TaskStatus
from schemas import FinishTaskRequest


async def get_task_info(session: AsyncSession, task_id: UUID):
    task = await session.execute(
    select(Task).options(joinedload(Task.task_target))
    )
    task = task.scalar_one_or_none()

    task_info = {
        "id": task.task_id,
        "status": task.status.value,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "type": task.type.value,
            "task_target": {
            "stock": task.task_target.stock,
            "item_id": str(task.task_target.item_id)
        },
        "posting_id": task.posting_id
    }
    return task_info


async def finish_task(session: AsyncSession, task_info: FinishTaskRequest):
    stmt = select(Task).where(Task.task_id == task_info.id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_info.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELED]:
        raise HTTPException(status_code=400, detail="Invalid status")

    task.status = task_info.status.value
    session.add(task)
    await session.commit()