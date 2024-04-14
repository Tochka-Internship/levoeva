from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import DiscountStatus, Discounts, Item, Sku, SkuItemStock, Task, TaskStatus
from queries.posting import find_similar_item
from schemas import ItemResponse, MarkdownItem, MoveToNotFound, SetSkuPrice, SkuItemsResponse, ToggleIsHidden


async def get_item_info(session: AsyncSession, item_id: UUID):
    stmt = select(Item).where(Item.item_id == item_id)

    item = await session.scalar(stmt)

    if item is None:
        None

    item_info = {
        "id": item.item_id,
        "sku_id": item.sku_id,
        "stock": item.stock.value,
        "reserved_state": item.reserved_state
    }

    return item_info


async def get_sku_info(session: AsyncSession, sku_id: UUID):
    stmt = select(Sku).where(Sku.sku_id == sku_id)

    sku = await session.scalar(stmt)

    if sku is None:
        None

    sku_info = {
        "id": sku.sku_id,
        "created_at": sku.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "actual_price": sku.actual_price,
        "base_price": sku.base_price,
        "count": sku.count,
        "is_hidden": sku.is_hidden
    }

    return sku_info


async def get_item_info_by_sku(session: AsyncSession,
                               sku_id: UUID) -> SkuItemsResponse:
    stmt = select(Item).where(Item.sku_id == sku_id)
    items_result = await session.execute(stmt)
    items = items_result.scalars().all()

    if not items:
        None

    items_info_list = [ItemResponse(
        item_id=item.item_id,
        stock=item.stock,
        reserved_state=item.reserved_state
    ) for item in items]

    return SkuItemsResponse(items=items_info_list)


async def markdown_item(session: AsyncSession, markdown_info: MarkdownItem):
    item_id = markdown_info.id
    percentage = Decimal(markdown_info.percentage) / 100
    item = await session.get(Item, item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    sku = await session.get(Sku, item.sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    if item.stock != SkuItemStock.DEFECT:
        item.stock = SkuItemStock.DEFECT

        sku_markdown_price = sku_markdown_price = sku.base_price * (
                Decimal('1') - percentage
                )

        discounts_statement = select(Discounts).where(
            Discounts.sku_id == sku.sku_id,
            Discounts.status == DiscountStatus.active
        )
        active_discounts = await session.execute(discounts_statement)
        for discount in active_discounts.scalars().all():
            potential_discounted_price = sku.base_price * (
                    Decimal('1') - Decimal(discount.percentage) / 100
                    )
            if potential_discounted_price < sku_markdown_price:
                sku_markdown_price = potential_discounted_price

        sku.actual_price = sku_markdown_price
        session.add(sku)

    await session.commit()

    tasks_stmt = await session.execute(
        select(Task).where(Task.task_target.contains({'Id': str(item_id),
                                                      'stock': (SkuItemStock.VALID)})))
    tasks_to_update = await session.execute(tasks_stmt)
    for task in tasks_to_update.scalars().all():
        if task.status == TaskStatus.IN_WORK:
            similar_item_id = await find_similar_item(session, item.sku_id,
                                                      SkuItemStock.VALID)
        if similar_item_id:
            task.task_target['Id'] = str(similar_item_id)
            task.task_target['stock'] = 'valid'
            session.add(task)
        else:
            task.status = TaskStatus.CANCELLED
            session.add(task)

    await session.commit()


async def set_sku_price(session: AsyncSession, price_info: SetSkuPrice):
    stmt = select(Sku).where(Sku.sku_id == price_info.sku_id)

    result = await session.execute(stmt)
    sku = result.scalar_one_or_none()

    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")

    sku.base_price = price_info.base_price

    await session.commit()


async def toggle_is_hidden(session: AsyncSession, toggle: ToggleIsHidden):
    stmt = select(Sku).where(Sku.sku_id == toggle.sku_id)

    result = await session.execute(stmt)
    sku = result.scalar_one_or_none()

    if sku is None:
        raise HTTPException(status_code=404, detail="SKU not found")

    sku.is_hidden = toggle.is_hidden

    await session.commit()


async def move_to_not_found(session: AsyncSession, item_info: MoveToNotFound):
    stmt = select(Item).where(Item.item_id == item_info.id)

    result = await session.execute(stmt)
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    item.stock = "not found"

    session.add(item)
    await session.commit()
