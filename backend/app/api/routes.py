from fastapi import APIRouter, HTTPException, Query

from app.schemas.search import (
    HealthResponse,
    IndexingSummaryResponse,
    IndexRepositoryRequest,
    SearchResponse,
    SearchResultResponse,
    SnippetLineResponse
)
from app.services.search_engine import SearchEngine

router = APIRouter()

# In-memory engine for now.
# Later, PostgreSQL will make this persistent across restarts.
search_engine = SearchEngine()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        indexed_documents=search_engine.total_documents(),
    )


@router.post("/index", response_model=IndexingSummaryResponse)
def index_repository(request: IndexRepositoryRequest) -> IndexingSummaryResponse:
    try:
        summary = search_engine.index_repository(request.repo_path)
        if summary.files_indexed == 0:
            raise HTTPException(
                status_code=422,
                detail="No supported source files were found to index.",
            )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NotADirectoryError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return IndexingSummaryResponse(
        repo_path=summary.repo_path,
        files_indexed=summary.files_indexed,
        total_tokens=summary.total_tokens,
        indexed_extensions=summary.indexed_extensions,
    )


@router.get("/search", response_model=SearchResponse)
def search(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    if not search_engine.is_ready():
        raise HTTPException(
            status_code=409,
            detail="No repository has been indexed yet. Call POST /index before searching.",
        )
    results = search_engine.search(query=query, limit=limit)

    response_results = [
        SearchResultResponse(
            document_id=result.document_id,
            relative_path=result.relative_path,
            score=result.score,
            matched_tokens=result.matched_tokens,
            line_numbers=result.line_numbers,
            snippets=[SnippetLineResponse(
                line_number=snippet.line_number,
                text=snippet.text,  
            ) for snippet in result.snippets
            ],
        )
        for result in results
    ]

    return SearchResponse(
        query=query,
        result_count=len(response_results),
        results=response_results,
    )