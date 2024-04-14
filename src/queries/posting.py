from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from models import Item, Posting, PostingStatus, Sku, SkuItemStock, Task, TaskStatus, TaskType
from schemas import CancelPostingRequest, CreatePostingRequest


async def get_posting_info(session: AsyncSession, posting_id: UUID):
    stmt = await session.execute(
        select(Posting)
        .options(
            joinedload(Posting.ordered_goods),
            joinedload(Posting.tasks),
        )
        .where(Posting.posting_id == posting_id)
    )

    posting = stmt.scalar_one_or_none()

    if not posting:
        return None

    posting_info = {
        "id": posting.posting_id,
        "status": posting.posting_status.value,
        "created_at": posting.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "cost": str(posting.cost),
        "ordered_goods": [],
        "not_found": [],
        "task_ids": [],
    }

    for item in posting.ordered_goods:
        ordered_goods_info = {
            "sku_id": item.sku_id,
            "from_valid_ids": [str(uuid) for uuid in item.from_valid_ids],
            "from_defect_ids": [str(uuid) for uuid in item.from_defect_ids],
        }
        posting_info["ordered_goods"].append(ordered_goods_info)

    for item in posting.not_found:
        item_info = {
            "sku_id": str(item.sku_id),
        }
        posting_info["not_found"].append(item_info)

    for task in posting.tasks:
        task_info = {
            "id": task.task_id,
            "type": task.type.value,
            "status": task.status.value,
        }
        posting_info["task_ids"].append(task_info)

    return posting_info


async def find_similar_item(session: AsyncSession, sku_id: UUID,
                            stock: SkuItemStock):
    stmt = select(Item).where(
        Item.sku_id == sku_id,
        Item.stock == stock,
        not Item.reserved_state
    ).limit(1)

    similar_item = await session.execute(stmt)
    similar_item = similar_item.scalars().first()

    return similar_item.item_id if similar_item else None


async def create_posting(session: AsyncSession,
                         posting_info: CreatePostingRequest):
    posting = Posting(
        cost = Decimal('0'),
        posting_status = PostingStatus.IN_ITEM_PICK
        )
    session.add(posting)
    await session.commit()


    total_cost = Decimal('0')
    tasks = []
    for order_goods in posting_info.ordered_goods:
        for item_id in (
             order_goods.from_valid_ids + order_goods.from_defect_ids):
                item = await session.get(Item, item_id)

                if item and not item.reserved_state:
                    item.reserved_state = True
                    sku = await session.get(Sku, item.sku_id)
                    item_cost = sku.actual_price
                    total_cost += item_cost

                    task_target = {"stock": item.stock.value, "Id": str(item.item_id)}
                    task_info = Task(
                        status=TaskStatus.IN_WORK,
                        created_at=datetime.utcnow(),
                        type=TaskType.PICKING,
                        task_target=task_target
                    )
                    tasks.append(task_info)

                else:
                    stock = SkuItemStock.VALID if item in (
                        order_goods.from_valid_ids) else SkuItemStock.DEFECT
                    similar_item_id = await find_similar_item(session,
                                                            order_goods.sku,
                                                            stock)
                    
                    if similar_item_id:
                        task_target = {"stock": stock, "Id": str(similar_item_id)}
                        task_info = Task(
                            status=TaskStatus.IN_WORK,
                            created_at=datetime.utcnow(),
                            type=TaskType.PICKING,
                            task_target=task_target,
                            posting_id=posting.posting_id,
                        )

                    else:
                        task_target = {"stock": stock, "Id": str(item_id)}
                        task_info = Task(
                            status=TaskStatus.CANCELED,
                            task_target=task_target,
                            posting_id=posting.posting_id,
                        )
                    new_item = Item(
                        sku_id=order_goods.sku, 
                        stock=SkuItemStock.NOT_FOUND
                    )
                    session.add(new_item)
                    tasks.append(task_info)

    posting.cost = total_cost
    session.add_all(tasks)
    await session.commit()

    return posting.posting_id


async def send_posting(session: AsyncSession, posting_id: UUID) -> None:
    posting = await session.get(Posting, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    tasks_stmt = select(Task).where(Task.posting_id == posting_id)
    tasks_result = await session.execute(tasks_stmt)
    tasks = tasks_result.scalars().all()

    if all(task.status == TaskStatus.COMPLETED for task in tasks):
        posting.status = PostingStatus.SENT
        session.add(posting)
    else:
        raise HTTPException(status_code=400,
                            detail="Not all tasks are completed")

    await session.commit()


async def cancel_posting(session: AsyncSession,
                         posting_info: CancelPostingRequest):
    result = await session.execute(select(Posting).where(
        Posting.posting_id == posting_info.id)
        )
    posting = result.scalar_one_or_none()

    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    if posting.posting_status == PostingStatus.IN_ITEM_PICK:
        posting.posting_status = PostingStatus.CANCELED
        tasks = await session.execute(
            select(Task).where(
                and_(Task.posting_id == posting_info.id,
                     Task.status.in_(TaskStatus.IN_WORK))
            )
        )

    tasks = tasks.scalars().all()
    for task in tasks:
        task.status = TaskStatus.CANCELED
        session.add(task)

    task = []
    for orders_goods in posting.ordered_goods:
        for item_id in (orders_goods.from_valid_ids
                        + orders_goods.from_defect_ids):
            stock = "valid" if item_id in (
                orders_goods.from_valid_ids) else "defect"
            item = await session.get(Item, item_id)
            if item and item.reserved_state:
                item.reserved_state = False
                session.add(item)

                task_target = {"Id": str(item.sku_id), "stock": stock}
                task_info = Task(
                    status=TaskStatus.IN_WORK,
                    created_at=datetime.utcnow(),
                    type=TaskType.PLACING,
                    task_target=task_target,
                    posting_id=posting.posting_id
                )
                task.append(task_info)

        session.add_all(task)
        await session.commit()

        return {"status": "Posting canceled successfully"}
    else:
        raise HTTPException(status_code=400,
                            detail="Posting cannot be canceled")