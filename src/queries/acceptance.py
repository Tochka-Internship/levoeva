from datetime import datetime
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from schemas import CreateAcceptanceRequest, ItemToAccept

from models import AcceptedItem, Item, SkuItemStock, Task, Sku, Acceptance, TaskType, TaskStatus


async def get_acceptance_info(session: AsyncSession, acceptance_id: UUID):
    stmt = await session.execute(
        select(Acceptance)
        .options(
            joinedload(Acceptance.accepted),
            joinedload(Acceptance.tasks),
        )
        .where(Acceptance.acceptance_id == acceptance_id)
    )
    acceptance = await session.scalar(stmt)

    if acceptance is None:
        None

    acceptance_info = {
        "id": acceptance.acceptance_id,
        "created_at": acceptance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "accepted": [],
        "task_ids": []
    }

    for item in acceptance.accepted:
        accept_info = {
            "sku_id": item.sku_id,
            "stock": item.stock.value,
            "count": item.count
        }
        acceptance_info["accepted"].append(accept_info)

    for task in acceptance.tasks:
        task_info = {
            "id": task.task_id,
            "status": task.status.value,
        }
        acceptance_info["task_ids"].append(task_info)

    return acceptance_info


async def create_acceptance(session: AsyncSession,
                            acceptance_info: CreateAcceptanceRequest):
    
    acceptance = Acceptance(created_at=datetime.utcnow())  
    session.add(acceptance)
    await session.commit()  
    await session.refresh(acceptance) 
 
    for item_to_accept in acceptance_info.items_to_accept: 
        stmt = select(Sku).where(Sku.sku_id == item_to_accept.sku_id) 
        result = await session.execute(stmt) 
        sku = result.scalar_one_or_none() 
 
        if sku is None: 
            sku = Sku( 
                sku_id=item_to_accept.sku_id,
                created_at=datetime.utcnow(),
                actual_price=Decimal("0.00"),
                base_price=Decimal("0.00"),
                count=item_to_accept.count,
                is_hidden=False
            ) 
            session.add(sku)
        

        accepted_item = AcceptedItem(
        sku_id=item_to_accept.sku_id,
        count=item_to_accept.count,
        stock = item_to_accept.stock.value.upper(),
        acceptance_id=acceptance.acceptance_id,
        )
        session.add(accepted_item)
            
 
        for _ in range(item_to_accept.count):
            new_item = Item(
                item_id=uuid4(),
                sku_id=item_to_accept.sku_id,
                stock=item_to_accept.stock.value.upper(),
                reserved_state=False
            )
            session.add(new_item)

            new_task = Task(
                acceptance_id = acceptance.acceptance_id,
                type=TaskType.PLACING,
                status=TaskStatus.IN_WORK,
                created_at=datetime.utcnow(),
                task_target_id=new_item.item_id
            )
            session.add(new_task)
            
        
    await session.commit()

    return acceptance.acceptance_id
