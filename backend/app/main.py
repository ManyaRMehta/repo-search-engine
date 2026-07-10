from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Repo Search Engine",
    description="A backend code search engine with repository crawling, tokenization, inverted indexing, and BM25 ranking.",
    version="0.1.0",
)

app.include_router(router)