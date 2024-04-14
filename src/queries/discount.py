from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import DiscountStatus, Discounts, Item, Sku, SkuItemStock
from schemas import CreateDiscountRequest


async def get_discount_info(session: AsyncSession, discount_id: UUID):
    result = await session.execute(select(Discounts).where(
        Discounts.discount_id == discount_id))
    discount = result.scalar_one_or_none()

    if discount is None:
        None

    discount_info = {
        "id": discount.discount_id,
        "status": discount.status.value,
        "created_at": discount.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "percentage": int(discount.percentage),
        "sku_ids": [str(sku_id) for sku_id in discount.sku_ids]
    }
    return discount_info()


async def create_discount_info(session: AsyncSession,
                               discount_info: CreateDiscountRequest) -> UUID:
    discount = Discounts(**discount_info.dict())
    session.add(discount)

    skus_to_update = []
    for sku_id in discount_info.sku_ids:
        sku = await session.get(Sku, sku_id)

        if sku is None:
            raise HTTPException(status_code=404,
                                detail=f"SKU {sku_id} not found")

        if sku.actual_price != sku.base_price:
            new_discounted_price = sku.base_price * (
                1 - Decimal(discount_info.percentage) / 100)

            if sku.actual_price is None or (
                        new_discounted_price < sku.actual_price):
                sku.actual_price = new_discounted_price
                skus_to_update.append(sku)

    if skus_to_update:
        session.add_all(skus_to_update)

    await session.commit()

    return discount.discount_id


async def cancel_discount(session: AsyncSession, discount_id: UUID):
    stmt = select(Discounts).where(Discounts.discount_id == discount_id)
    discount = await session.scalar(stmt)
    if not discount or discount.status != DiscountStatus.active:
        raise HTTPException(status_code=404,
                            detail="Discount not found or not active")

    discount.status = DiscountStatus.finished

    items_result = await session.execute(
        select(Item).where(Item.sku_id.in_(discount.sku_ids),
                           Item.stock != SkuItemStock.DEFECT)
    )
    items = items_result.scalars().all()

    skus_updated = set()
    for item in items:
        sku = await session.get(Sku, item.sku_id)
        if sku and sku.sku_id not in skus_updated:
            sku.actual_price = sku.base_price
            session.add(sku)
            skus_updated.add(sku.id)

    await session.commit()

    return discount.status.value