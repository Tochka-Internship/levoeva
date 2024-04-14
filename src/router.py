from uuid import UUID

from fastapi import APIRouter, HTTPException

from di import SessionDep
from queries.acceptance import create_acceptance, get_acceptance_info
from queries.discount import cancel_discount, create_discount_info, get_discount_info
from queries.items import get_item_info, get_item_info_by_sku, get_sku_info, markdown_item, move_to_not_found, set_sku_price, toggle_is_hidden
from queries.posting import cancel_posting, create_posting, get_posting_info
from queries.tasks import finish_task, get_task_info
from schemas import (Posting, Task, Item, SKU, Discount, CreatePostingRequest,
                     CreatePostingResponse, FinishTaskRequest,
                     CreateDiscountRequest,
                     CreateDiscountResponse, SkuItemsResponse,
                     CreateAcceptanceRequest,
                     CreateAcceptanceResponse,
                     SetSkuPrice, ToggleIsHidden, MarkdownItem, Acceptance,
                     CancelPostingRequest)



router = APIRouter()


@router.get("/getPosting/{posting_id}", response_model=Posting)
async def get_posting_info_endpoint(posting_id: UUID, session: SessionDep):
    data = await get_posting_info(session, posting_id)
    if not data:
        raise HTTPException(status_code=404, detail="Posting not found")
    return data


@router.post("/createPostnig", response_model=CreatePostingResponse)
async def create_posting_endpoint(posting: CreatePostingRequest,
                                  session: SessionDep):
        posting_id = await create_posting(session, posting)

        return CreatePostingResponse(id=posting_id)


@router.post("/cancelPosting")
async def cancel_posting_endpoint(cancel_posting_request: CancelPostingRequest,
                                  session: SessionDep):
        await cancel_posting(session, cancel_posting_request)
        return {"detail": "Posting canceled successfully"}


@router.get("/getTaskInfo/{task_id}", response_model=Task)
async def get_task_info_endpoint(task_id: UUID, session: SessionDep):
        data = await get_task_info(session, task_id)
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        return data


@router.post("/finishTask")
async def finish_task_endpoint(task: FinishTaskRequest,
                               session: SessionDep):
        await finish_task(session, task)
        return {"detail": "Task updated successfully"}


@router.get("/getDiscount/{discount_id}", response_model=Discount)
async def get_discount_info_endpoint(discount_id: UUID, session: SessionDep):
        data = await get_discount_info(session, discount_id)
        if not data:
            raise HTTPException(status_code=404, detail="Task not found")
        return data


@router.post("/createDiscount", response_model=CreateDiscountResponse)
async def create_discount_info_endpoint(discount: CreateDiscountRequest,
                                        session: SessionDep):
        discount_id = await create_discount_info(session, discount)

        return CreateDiscountResponse(id=discount_id)


@router.post("/cancelDiscount")
async def cancel_discount_endpoint(id: UUID, session: SessionDep):
        await cancel_discount(session, id)
        return {"detail": "Discount canceled successfully"}


@router.get("/geItemInfo/{item_id}", response_model=Item)
async def get_item_info_endpoint(item_id: UUID, session: SessionDep):
        data = await get_item_info(session, item_id)
        if not data:
            raise HTTPException(status_code=404, detail="Item not found")
        return data


@router.get("/getSkuInfo/{sku_id}", response_model=SKU)
async def get_sku_info_endpoint(sku_id: UUID, session: SessionDep):
        data = await get_sku_info(session, sku_id)
        if not data:
            raise HTTPException(status_code=404, detail="SKU not found")
        return data


@router.get("/getItemInfoBySkuId/{sku_id}", response_model=SkuItemsResponse)
async def get_item_info_by_sku_endpoint(sku_id: UUID, session: SessionDep):
        data = await get_item_info_by_sku(session, sku_id)
        if not data:
            raise HTTPException(status_code=404, detail="SKU not found")
        return data


@router.post("/markdownItem")
async def markdown_item_endpoint(reqest: MarkdownItem, session: SessionDep):
        await markdown_item(session, reqest)
        return {"item markown successfully"}


@router.post("/setSkuPrice")
async def set_sku_price_endpoint(request: SetSkuPrice, session: SessionDep):
        await set_sku_price(session, request)
        return {"Price changed successfully"}


@router.post("/toggleIsHidden")
async def toggle_is_hidden_endpoint(request: ToggleIsHidden,
                                    session: SessionDep):
        await toggle_is_hidden(session, request)
        return {"Successful"}


@router.post("/moveToNotFound")
async def move_to_not_found_endpoint(id: UUID, session: SessionDep):
        await move_to_not_found(session, id)
        return {"Item stasus: not found"}


@router.get("/getAcceptance/{acceptance_id}", response_model=Acceptance)
async def get_acceptance_info_endpoint(acceptance_id: UUID,
                                       session: SessionDep) -> Acceptance:
        data = await get_acceptance_info(session, acceptance_id)
        if not data:
            raise HTTPException(status_code=404, detail="Acceptance not found")
        return data


@router.post("/createAcceptance", response_model=CreateAcceptanceResponse)
async def create_acceptance_endpoint(acceptance: CreateAcceptanceRequest,
                                     session: SessionDep):

        acceptance_id = await create_acceptance(session, acceptance)

        return CreateAcceptanceResponse(id=acceptance_id)
