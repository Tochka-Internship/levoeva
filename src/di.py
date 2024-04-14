from typing import AsyncIterable, Annotated

from database import async_session_factory

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def provide_session() -> AsyncIterable[AsyncSession]:
    async with async_session_factory() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(provide_session)]
