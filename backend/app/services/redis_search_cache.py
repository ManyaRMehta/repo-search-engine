from typing import Protocol

from redis.exceptions import RedisError

from app.models.search_result import SearchResult
from app.services.search_cache import (
    SearchCacheError,
)
from app.services.search_cache_key import (
    SearchCacheKeyBuilder,
)
from app.services.search_cache_serialization import (
    SearchCacheSerializationError,
    deserialize_search_results,
    serialize_search_results,
)


class RedisClient(Protocol):
    """The small subset of Redis operations this cache requires."""

    def get(
        self,
        key: str,
    ) -> str | bytes | None:
        ...

    def set(
        self,
        name: str,
        value: str,
        *,
        ex: int,
    ) -> object:
        ...


class RedisSearchCache:
    """Stores versioned search results in Redis."""

    def __init__(
        self,
        *,
        client: RedisClient,
        key_builder: SearchCacheKeyBuilder,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError(
                "Search-cache TTL must be greater than zero."
            )

        self.client = client
        self.key_builder = key_builder
        self.ttl_seconds = ttl_seconds

    def get(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
    ) -> list[SearchResult] | None:
        key = self.key_builder.build(
            repository_id=repository_id,
            index_version=index_version,
            query=query,
            limit=limit,
        )

        try:
            payload = self.client.get(key)
        except RedisError as error:
            raise SearchCacheError(
                "Redis search-cache read failed."
            ) from error

        if payload is None:
            return None

        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            return deserialize_search_results(payload)
        except (
            UnicodeDecodeError,
            SearchCacheSerializationError,
        ) as error:
            raise SearchCacheError(
                "Cached search results could not be decoded."
            ) from error

    def set(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
        results: list[SearchResult],
    ) -> None:
        key = self.key_builder.build(
            repository_id=repository_id,
            index_version=index_version,
            query=query,
            limit=limit,
        )

        payload = serialize_search_results(results)

        try:
            self.client.set(
                key,
                payload,
                ex=self.ttl_seconds,
            )
        except RedisError as error:
            raise SearchCacheError(
                "Redis search-cache write failed."
            ) from error