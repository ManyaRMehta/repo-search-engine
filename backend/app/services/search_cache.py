from typing import Protocol

from app.models.search_result import SearchResult

class SearchCacheError(RuntimeError):
    """Raised when the search cache cannot complete an operation."""

class SearchCache(Protocol):
    """Defines the cache behavior required by SearchService."""

    def get(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
    ) -> list[SearchResult] | None:
        """Return cached results, or None when no cached value exists."""
        ...

    def set(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
        results: list[SearchResult],
    ) -> None:
        """Store search results for one repository generation."""
        ...