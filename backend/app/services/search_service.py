from app.models.search_result import SearchResult
from app.services.search_cache import SearchCache, SearchCacheError
from app.services.search_engine import SearchEngine


class SearchService:
    """Coordinates cached search execution."""

    def __init__(
        self,
        *,
        search_engine: SearchEngine,
        cache: SearchCache,
    ) -> None:
        self.search_engine = search_engine
        self.cache = cache

    def search(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        state = self.search_engine.current_runtime_state()

        if (
            state.repository_id is None
            or state.index_version is None
        ):
            return self.search_engine.search_state(
                state,
                query=query,
                limit=limit,
            )

        try:
            cached_results = self.cache.get(
                repository_id=state.repository_id,
                index_version=state.index_version,
                query=query,
                limit=limit,
            )
        except SearchCacheError:
            return self.search_engine.search_state(
                state,
                query=query,
                limit=limit,
            )

        if cached_results is not None:
            return cached_results

        results = self.search_engine.search_state(
            state,
            query=query,
            limit=limit,
        )

        try:
            self.cache.set(
                repository_id=state.repository_id,
                index_version=state.index_version,
                query=query,
                limit=limit,
                results=results,
            )
        except SearchCacheError:
            pass

        return results