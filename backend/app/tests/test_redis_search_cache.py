from app.models.search_result import SearchResult, SnippetLine
from app.services.redis_search_cache import RedisSearchCache
from app.services.search_cache_key import SearchCacheKeyBuilder
import pytest
import time
from redis.exceptions import ConnectionError
from redis import Redis
from app.services.search_cache import SearchCacheError


class FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int]] = []

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(
        self,
        name: str,
        value: str,
        *,
        ex: int,
    ) -> bool:
        self.values[name] = value
        self.set_calls.append((name, value, ex))
        return True


def test_redis_search_cache_round_trips_results_with_ttl() -> None:
    client = FakeRedisClient()
    key_builder = SearchCacheKeyBuilder()

    cache = RedisSearchCache(
        client=client,
        key_builder=key_builder,
        ttl_seconds=900,
    )

    original_results = [
        SearchResult(
            document_id=42,
            relative_path="app/auth.py",
            score=3.75,
            matched_tokens=["jwt"],
            line_numbers=[10],
            snippets=[
                SnippetLine(
                    line_number=10,
                    text="def validate_jwt_token(token):",
                )
            ],
        )
    ]

    cache.set(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
        results=original_results,
    )

    restored_results = cache.get(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    )

    assert restored_results == original_results
    assert len(client.set_calls) == 1
    assert client.set_calls[0][2] == 900

def test_redis_search_cache_returns_none_on_miss() -> None:
    client = FakeRedisClient()
    cache = RedisSearchCache(
        client=client,
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    results = cache.get(
        repository_id=7,
        index_version=3,
        query="missing query",
        limit=5,
    )

    assert results is None

class ReadFailureRedisClient(FakeRedisClient):
    def get(self, key: str) -> str | None:
        raise ConnectionError("Redis unavailable")
    
def test_redis_search_cache_translates_redis_read_failure() -> None:
    cache = RedisSearchCache(
        client=ReadFailureRedisClient(),
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    with pytest.raises(
        SearchCacheError,
        match="Redis search-cache read failed",
    ):
        cache.get(
            repository_id=7,
            index_version=3,
            query="jwt",
            limit=5,
        )

class WriteFailureRedisClient(FakeRedisClient):
    def set(
        self,
        name: str,
        value: str,
        *,
        ex: int,
    ) -> bool:
        raise ConnectionError("Redis unavailable")
    
def test_redis_search_cache_translates_redis_write_failure() -> None:
    cache = RedisSearchCache(
        client=WriteFailureRedisClient(),
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    with pytest.raises(
        SearchCacheError,
        match="Redis search-cache write failed",
    ):
        cache.set(
            repository_id=7,
            index_version=3,
            query="jwt",
            limit=5,
            results=[],
        )

class CorruptPayloadRedisClient(FakeRedisClient):
    def get(self, key: str) -> str | None:
        return "not valid json"
    
def test_redis_search_cache_translates_corrupt_payload() -> None:
    cache = RedisSearchCache(
        client=CorruptPayloadRedisClient(),
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    with pytest.raises(
        SearchCacheError,
        match="Cached search results could not be decoded",
    ):
        cache.get(
            repository_id=7,
            index_version=3,
            query="jwt",
            limit=5,
        )

class BytesPayloadRedisClient(FakeRedisClient):
    def get(self, key: str) -> bytes | None:
        value = self.values.get(key)

        if value is None:
            return None

        return value.encode("utf-8")
    
def test_redis_search_cache_decodes_byte_payloads() -> None:
    client = BytesPayloadRedisClient()
    cache = RedisSearchCache(
        client=client,
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    original_results = [
        SearchResult(
            document_id=42,
            relative_path="app/auth.py",
            score=3.75,
            matched_tokens=["jwt"],
            line_numbers=[10],
            snippets=[
                SnippetLine(
                    line_number=10,
                    text="def validate_jwt_token(token):",
                )
            ],
        )
    ]

    cache.set(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
        results=original_results,
    )

    restored_results = cache.get(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    )

    assert restored_results == original_results

def test_redis_search_cache_round_trips_results_with_real_redis(
    redis_client: Redis,
) -> None:
    cache = RedisSearchCache(
        client=redis_client,
        key_builder=SearchCacheKeyBuilder(),
        ttl_seconds=900,
    )

    original_results = [
        SearchResult(
            document_id=42,
            relative_path="app/auth.py",
            score=3.75,
            matched_tokens=["jwt"],
            line_numbers=[10],
            snippets=[
                SnippetLine(
                    line_number=10,
                    text="def validate_jwt_token(token):",
                )
            ],
        )
    ]

    cache.set(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
        results=original_results,
    )

    restored_results = cache.get(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    )

    assert restored_results == original_results

def test_redis_search_cache_expires_results_after_ttl(
    redis_client: Redis,
) -> None:
    key_builder = SearchCacheKeyBuilder()

    cache = RedisSearchCache(
        client=redis_client,
        key_builder=key_builder,
        ttl_seconds=1,
    )

    cache.set(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
        results=[],
    )

    key = key_builder.build(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    )

    assert redis_client.exists(key) == 1

    deadline = time.monotonic() + 2

    while (
        redis_client.exists(key)
        and time.monotonic() < deadline
    ):
        time.sleep(0.05)

    assert redis_client.exists(key) == 0

    assert cache.get(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    ) is None

def test_redis_search_cache_isolates_index_versions(
    redis_client: Redis,
) -> None:
    key_builder = SearchCacheKeyBuilder()

    cache = RedisSearchCache(
        client=redis_client,
        key_builder=key_builder,
        ttl_seconds=900,
    )

    version_three_results = [
        SearchResult(
            document_id=42,
            relative_path="app/auth.py",
            score=3.75,
            matched_tokens=["jwt"],
            line_numbers=[10],
            snippets=[],
        )
    ]

    cache.set(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
        results=version_three_results,
    )

    version_three_key = key_builder.build(
        repository_id=7,
        index_version=3,
        query="jwt",
        limit=5,
    )

    version_four_key = key_builder.build(
        repository_id=7,
        index_version=4,
        query="jwt",
        limit=5,
    )

    assert redis_client.exists(version_three_key) == 1
    assert redis_client.exists(version_four_key) == 0

    version_four_results = cache.get(
        repository_id=7,
        index_version=4,
        query="jwt",
        limit=5,
    )

    assert version_four_results is None

    # The old entry still exists until its TTL expires, but new
    # requests cannot reach it because they use the new version.
    assert redis_client.exists(version_three_key) == 1