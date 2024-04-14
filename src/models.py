import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, Column, ForeignKey, Table, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, NUMERIC

from database import Base


class SkuItemStock(enum.Enum):
    VALID = "valid"
    DEFECT = "defect"
    NOT_FOUND = "not_found"


class TaskStatus(enum.Enum):
    COMPLETED = "completed"
    IN_WORK = "in_work"
    CANCELED = "canceled"


class TaskType(enum.Enum):
    PICKING = "picking"
    PLACING = "placing"


class PostingStatus(enum.Enum):
    IN_ITEM_PICK = "in_item_pick"
    SENT = "sent"
    CANCELED = "canceled"



class DiscountStatus (enum.Enum):
    active = "active"
    finished = "finished"
    

class Sku(Base):
    __tablename__ = "sku"

    sku_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                              default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )   
    actual_price: Mapped[Decimal] = mapped_column(NUMERIC(10, 2))
    base_price: Mapped[Decimal] = mapped_column(NUMERIC(10, 2))
    count: Mapped[int]
    is_hidden: Mapped[bool]

    sku_items: Mapped[list["Item"]] = relationship(back_populates="sku")


class Item(Base):
    __tablename__ = "item"

    item_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                               default=uuid.uuid4)
    sku_id: Mapped[UUID] = mapped_column(ForeignKey("sku.sku_id"))
    stock: Mapped[SkuItemStock]
    reserved_state: Mapped[bool] = mapped_column(default=False)

    sku: Mapped["Sku"] = relationship(back_populates="sku_items")
    tasks: Mapped["Task"] =  relationship(back_populates="task_target")


class OrderedGood(Base):
    __tablename__ = 'ordered_goods'

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                          default=uuid.uuid4)
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey('sku.sku_id'))
    posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey('posting.posting_id')
        )

    from_valid_ids: Mapped[list["Item"]] = relationship(
        "Item", 
        primaryjoin="and_(OrderedGood.sku_id==foreign(Item.sku_id), "
                    "Item.stock=='VALID')",
        viewonly=True,
    )

   
    from_defect_ids: Mapped[list["Item"]] = relationship(
        "Item",
        primaryjoin="and_(OrderedGood.sku_id==foreign(Item.sku_id), "
                    "Item.stock=='DEFECT')",
        viewonly=True,
    )


    posting: Mapped["Posting"] = relationship(back_populates="ordered_goods")


class Posting(Base):
    __tablename__ = "posting"

    posting_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                                  default=uuid.uuid4)
    posting_status: Mapped[PostingStatus]
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )   
    cost: Mapped[Decimal] = mapped_column(NUMERIC(10, 2))
    not_found: Mapped[list[uuid.UUID]] = mapped_column(UUID, nullable=True)
    ordered_goods: Mapped[list["OrderedGood"]] = relationship(
        back_populates="posting",
        )
    tasks: Mapped [list["Task"]] = relationship(back_populates="posting")


class Task(Base):
    __tablename__ = "task"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                               default=uuid.uuid4)
    acceptance_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("acceptance.acceptance_id"),
        nullable=True
        )
    type: Mapped[TaskType]
    status: Mapped[TaskStatus]
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )   
    task_target_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey('item.item_id'),
        )
    posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("posting.posting_id"),
        nullable=True
        )

    task_target: Mapped["Item"] = relationship(back_populates="tasks",
                                               uselist=False
                                               )
    posting: Mapped["Posting"] = relationship(back_populates="tasks")

    acceptance: Mapped["Acceptance"] = relationship(back_populates="tasks")

    


class Acceptance(Base):
    __tablename__ = "acceptance"

    acceptance_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                                     default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )   
    accepted: Mapped[list["AcceptedItem"]] = relationship(
        back_populates="acceptance"
        )

    tasks:Mapped["Task"] = relationship(back_populates="acceptance")


discount_sku_association = Table(
    'discount_sku_association', Base.metadata,
    Column('discount_id', UUID(as_uuid=True),
           ForeignKey('discount.discount_id'), primary_key=True
           ),
    Column('sku_id', UUID(as_uuid=True), ForeignKey('sku.sku_id'),
           primary_key=True
           )
)


class Discounts(Base):
    __tablename__ = "discount"

    discount_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True,
                                                   default=uuid.uuid4)
    status: Mapped[DiscountStatus]
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )   
    percentage: Mapped[int] = mapped_column(default=10)
    sku_ids: Mapped[list[Sku]] = relationship(
        'Sku',
        secondary=discount_sku_association,
        backref='discounts'
    )


class AcceptedItem(Base):
    __tablename__ = 'accepted_items'

    id: Mapped[uuid.UUID] = mapped_column(UUID,
                                          primary_key=True,
                                          default=uuid.uuid4
                                          )
    sku_id: Mapped[uuid.UUID] = mapped_column(UUID,
                                              ForeignKey("sku.sku_id"),
                                              )
    stock: Mapped[SkuItemStock]
    count: Mapped[int]
    acceptance_id: Mapped[uuid.UUID] = mapped_column(
                                        UUID,
                                        ForeignKey("acceptance.acceptance_id"),
                                        )
    acceptance: Mapped["Acceptance"] = relationship(back_populates='accepted')
