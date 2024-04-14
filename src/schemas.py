from decimal import Decimal
from uuid import UUID
from enum import Enum
from typing import List


from pydantic import BaseModel


class StockStateEnum(str, Enum):
    VALID = "valid"
    DEFECT = "defect"
    NOT_FOUND = "not_found"


class TaskTypeEnum(str, Enum):
    PICKING = "picking"
    PLACING = "placing"


class TaskStatusEnum(str, Enum):
    COMPLETED = "completed"
    IN_WORK = "in_work"
    CANCELED = "canceled"


class PostingStatusEnum(str, Enum):
    IN_ITEM_PICK = "in_item_pick"
    SENT = "sent"
    CANCELED = "canceled"


class DiscountStatus (str, Enum):
    active = "active"
    finished = "finished"


class TaskStatusInfo(BaseModel):
    task_id: UUID
    status: TaskStatusEnum


class Item(BaseModel):
    id: UUID
    sku_id: UUID
    stock_state: StockStateEnum
    reserved_state: bool


class SKU(BaseModel):
    id: UUID
    created_at: str
    actual_price: Decimal
    base_price: Decimal
    count: int
    is_hidden: bool


class Task(BaseModel):
    id: UUID
    type: TaskTypeEnum
    status: TaskStatusEnum
    posting_id: UUID
    stock_state: StockStateEnum
    stock_item_id: UUID


class PostingTask(BaseModel):
    id: UUID
    type: TaskTypeEnum
    status: TaskStatusEnum


class Posting(BaseModel):
    posting_id: UUID
    posting_status: PostingStatusEnum
    created_at: str
    cost: Decimal
    ordered_goods: List["OrderedGood"]
    not_found: List[UUID]
    task_ids: List["PostingTask"]


class Discount(BaseModel):
    id: UUID
    status: DiscountStatus
    created_at: str
    percentage: int = 10
    sku_ids: List[UUID]


class ItemToAccept(BaseModel):
    sku_id: UUID
    stock: StockStateEnum
    count: int


class Acceptance(BaseModel):
    id: UUID
    created_at: str
    accepted: List[ItemToAccept]
    task_ids: List[TaskStatusInfo]


class ItemResponse(BaseModel):
    item_id: UUID
    stock: StockStateEnum
    reserved_state: bool


class SkuItemsResponse(BaseModel):
    items: List[ItemResponse]


class OrderedGood(BaseModel):
    sku: UUID
    from_valid_ids: List[UUID]
    from_defect_ids: List[UUID]


class CreateAcceptanceRequest(BaseModel):
    items_to_accept: List[ItemToAccept]


class CreatePostingRequest(BaseModel):
    ordered_goods: List[OrderedGood]


class CreatePostingResponse(BaseModel):
    id: UUID


class CancelPostingRequest(BaseModel):
    id: UUID
    status: PostingStatusEnum


class FinishTaskRequest(BaseModel):
    id: UUID
    status: TaskStatusEnum


class CreateDiscountRequest(BaseModel):
    sku_ids: List[UUID] = []
    percentage: int = 10


class CreateDiscountResponse(BaseModel):
    id: UUID


class CancelDiscountRequest(BaseModel):
    id: UUID


class MarkdownItem(BaseModel):
    id: UUID
    percentage: int


class SetSkuPrice(BaseModel):
    sku_id: UUID
    base_price: Decimal


class ToggleIsHidden(BaseModel):
    sku_id: UUID
    is_hidden: bool


class MoveToNotFound(BaseModel):
    id: UUID


class CreateAcceptanceResponse(BaseModel):
    id: UUID
