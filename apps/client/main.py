import logging
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.client.database import engine, get_session
from apps.client.models import Base, User
from apps.client.schemas import UserCreate, UserRead

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(
    title="Client API",
    description="API cliente que consulta a Server API e persiste usuários.",
    version="1.0.0",
    lifespan=lifespan,
)

SERVER_API_URL = "http://127.0.0.1:8000/users"
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "client",
        "status": "running",
    }


@app.get("/users")
async def get_users() -> dict:
    logger.info("Iniciando consulta de usuários na Server API")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(SERVER_API_URL)
            response.raise_for_status()

        users = response.json()
        logger.info(
            "Consulta à Server API concluída: total=%d",
            len(users),
        )

        return {
            "source": "server-api",
            "total": len(users),
            "users": users,
        }

    except httpx.TimeoutException as error:
        logger.warning(
            "Timeout ao consultar a Server API",
            exc_info=True,
        )
        raise HTTPException(
            status_code=504,
            detail="A Server API demorou demais para responder.",
        ) from error

    except httpx.HTTPStatusError as error:
        logger.error(
            "Server API retornou status inesperado: status=%d",
            error.response.status_code,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail=f"A Server API retornou o status {error.response.status_code}.",
        ) from error

    except httpx.RequestError as error:
        logger.exception("Falha de comunicação com a Server API")
        raise HTTPException(
            status_code=503,
            detail="Não foi possível acessar a Server API.",
        ) from error


@app.post(
    "/stored-users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_stored_user(
    user: UserCreate,
    session: DatabaseSession,
) -> UserRead:
    stored_user = User(
        name=user.name,
        username=user.username,
        email=user.email,
    )
    session.add(stored_user)

    try:
        await session.commit()
        await session.refresh(stored_user)
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um usuário com esse username ou email.",
        ) from error

    return UserRead(
        id=stored_user.id,
        name=stored_user.name,
        username=stored_user.username,
        email=stored_user.email,
    )


@app.get("/stored-users", response_model=list[UserRead])
async def get_stored_users(session: DatabaseSession) -> list[UserRead]:
    result = await session.scalars(select(User).order_by(User.id))

    return [
        UserRead(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
        )
        for user in result
    ]
