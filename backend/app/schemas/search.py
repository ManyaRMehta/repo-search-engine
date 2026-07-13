from pydantic import BaseModel


class IndexRepositoryRequest(BaseModel):
    repo_path: str


class IndexingSummaryResponse(BaseModel):
    repo_path: str
    files_indexed: int
    total_tokens: int
    indexed_extensions: list[str]

class SnippetLineResponse(BaseModel):
    line_number: int
    text: str

class SearchResultResponse(BaseModel):
    document_id: int
    relative_path: str
    score: float
    matched_tokens: list[str]
    line_numbers: list[int]
    snippets: list[SnippetLineResponse]


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[SearchResultResponse]


class HealthResponse(BaseModel):
    status: str
    indexed_documents: int

class AutocompleteResponse(BaseModel):
    prefix: str
    suggestion_count: int
    suggestions: list[str]