import logging

import httpx
from fastapi import FastAPI, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Client API",
    description="API cliente que consulta a Server API.",
    version="1.0.0",
)

SERVER_API_URL = "http://127.0.0.1:8000/users"


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
