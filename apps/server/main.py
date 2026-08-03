import logging

import httpx
from fastapi import FastAPI, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Server API",
    description="API intermediária que consulta o JSONPlaceholder.",
    version="1.0.0",
)

EXTERNAL_API_URL = "https://jsonplaceholder.typicode.com/users"


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "server",
        "status": "running",
    }


@app.get("/users")
async def get_users() -> list[dict]:
    logger.info("Iniciando consulta de usuários no JSONPlaceholder")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(EXTERNAL_API_URL)
            response.raise_for_status()

        logger.info(
            "Consulta ao JSONPlaceholder concluída: status=%d",
            response.status_code,
        )
        return response.json()

    except httpx.TimeoutException as error:
        logger.warning(
            "Timeout ao consultar o JSONPlaceholder",
            exc_info=True,
        )
        raise HTTPException(
            status_code=504,
            detail="A API externa demorou demais para responder.",
        ) from error

    except httpx.HTTPStatusError as error:
        logger.error(
            "JSONPlaceholder retornou status inesperado: status=%d",
            error.response.status_code,
            exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail=f"A API externa retornou o status {error.response.status_code}.",
        ) from error

    except httpx.RequestError as error:
        logger.exception("Falha de comunicação com o JSONPlaceholder")
        raise HTTPException(
            status_code=502,
            detail="Não foi possível acessar a API externa.",
        ) from error
