from pathlib import Path

from app.models.search_result import SearchResult
from app.models.source_file import SourceFile
from app.services.search_engine import SearchEngine
from app.services.search_service import SearchService
from app.services.search_cache import SearchCacheError

    
class FakeSearchCache:
    def __init__(
        self,
        cached_results: list[SearchResult] | None = None,
    ) -> None:
        self.cached_results = cached_results
        self.get_calls: list[tuple[int, int, str, int]] = []
        self.set_calls: list[
            tuple[int, int, str, int, list[SearchResult]]
        ] = []

    def get(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
    ) -> list[SearchResult] | None:
        self.get_calls.append(
            (
                repository_id,
                index_version,
                query,
                limit,
            )
        )

        return self.cached_results

    def set(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
        results: list[SearchResult],
    ) -> None:
        self.set_calls.append(
            (
                repository_id,
                index_version,
                query,
                limit,
                results,
            )
        )


def test_search_service_runs_search_and_caches_results_on_miss(
    tmp_path: Path,
) -> None:
    search_engine = SearchEngine()

    content = "jwt token validation"
    source_file = SourceFile(
        path=tmp_path / "auth.py",
        relative_path="auth.py",
        extension=".py",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(42, source_file)],
        repository_id=7,
        index_version=3,
    )
    search_engine.activate_runtime_state(state)

    cache = FakeSearchCache()
    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    results = service.search(
        query="jwt token",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].document_id == 42

    assert cache.get_calls == [
        (7, 3, "jwt token", 5)
    ]

    assert cache.set_calls == [
        (7, 3, "jwt token", 5, results)
    ]

def test_search_service_returns_cached_results_without_running_search(
    tmp_path: Path,
    monkeypatch,
) -> None:
    search_engine = SearchEngine()

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[],
        repository_id=7,
        index_version=3,
    )
    search_engine.activate_runtime_state(state)

    cached_results = [
        SearchResult(
            document_id=42,
            relative_path="auth.py",
            score=3.5,
            matched_tokens=["jwt"],
            line_numbers=[10],
            snippets=[],
        )
    ]

    cache = FakeSearchCache(
        cached_results=cached_results,
    )
    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    def fail_if_search_runs(*args, **kwargs):
        raise AssertionError(
            "BM25 search should not run on a cache hit."
        )

    monkeypatch.setattr(
        search_engine,
        "search_state",
        fail_if_search_runs,
    )

    results = service.search(
        query="jwt",
        limit=5,
    )

    assert results == cached_results
    assert cache.get_calls == [
        (7, 3, "jwt", 5)
    ]
    assert cache.set_calls == []

def test_search_service_treats_cached_empty_results_as_a_hit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    search_engine = SearchEngine()

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[],
        repository_id=7,
        index_version=3,
    )
    search_engine.activate_runtime_state(state)

    cache = FakeSearchCache(cached_results=[])
    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    def fail_if_search_runs(*args, **kwargs):
        raise AssertionError(
            "BM25 search should not run for cached empty results."
        )

    monkeypatch.setattr(
        search_engine,
        "search_state",
        fail_if_search_runs,
    )

    results = service.search(
        query="nonexistent",
        limit=5,
    )

    assert results == []
    assert cache.get_calls == [
        (7, 3, "nonexistent", 5)
    ]
    assert cache.set_calls == []




class ReadFailureSearchCache(FakeSearchCache):
    def get(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
    ) -> list[SearchResult] | None:
        raise SearchCacheError("cache read failed")
    
def test_search_service_falls_back_when_cache_read_fails(
    tmp_path: Path,
) -> None:
    search_engine = SearchEngine()

    content = "jwt token validation"
    source_file = SourceFile(
        path=tmp_path / "auth.py",
        relative_path="auth.py",
        extension=".py",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(42, source_file)],
        repository_id=7,
        index_version=3,
    )
    search_engine.activate_runtime_state(state)

    cache = ReadFailureSearchCache()
    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    results = service.search(
        query="jwt",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].document_id == 42

class WriteFailureSearchCache(FakeSearchCache):
    def set(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
        results: list[SearchResult],
    ) -> None:
        raise SearchCacheError("cache write failed")
    
def test_search_service_returns_results_when_cache_write_fails(
    tmp_path: Path,
) -> None:
    search_engine = SearchEngine()

    content = "jwt token validation"
    source_file = SourceFile(
        path=tmp_path / "auth.py",
        relative_path="auth.py",
        extension=".py",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(42, source_file)],
        repository_id=7,
        index_version=3,
    )
    search_engine.activate_runtime_state(state)

    cache = WriteFailureSearchCache()
    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    results = service.search(
        query="jwt",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].document_id == 42

def test_search_service_bypasses_cache_without_repository_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    search_engine = SearchEngine()

    content = "jwt token validation"
    source_file = SourceFile(
        path=tmp_path / "auth.py",
        relative_path="auth.py",
        extension=".py",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )

    state = search_engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(42, source_file)],
    )
    search_engine.activate_runtime_state(state)

    cache = FakeSearchCache()

    def fail_if_cache_runs(*args, **kwargs):
        raise AssertionError(
            "Cache should not be used without repository identity."
        )

    monkeypatch.setattr(cache, "get", fail_if_cache_runs)
    monkeypatch.setattr(cache, "set", fail_if_cache_runs)

    service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    results = service.search(
        query="jwt",
        limit=5,
    )

    assert len(results) == 1
    assert results[0].document_id == 42