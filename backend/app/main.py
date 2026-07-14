from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router
from app.runtime import indexing_service


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    indexing_service.hydrate_active_repository()
    yield


app = FastAPI(
    title="Repo Search Engine",
    description=(
        "A backend code search engine with repository crawling, "
        "tokenization, inverted indexing, BM25 ranking, and "
        "persistent repository storage."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router)