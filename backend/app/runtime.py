from redis import Redis

from app.config import (
    REDIS_CONNECT_TIMEOUT_SECONDS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
    REDIS_URL,
    SEARCH_CACHE_TTL_SECONDS,
)
from app.services.indexing_service import IndexingService
from app.services.redis_search_cache import RedisSearchCache
from app.services.search_cache_key import SearchCacheKeyBuilder
from app.services.search_engine import SearchEngine
from app.services.search_service import SearchService


search_engine = SearchEngine()

redis_client = Redis.from_url(
    REDIS_URL,
    socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
    socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
)

search_cache = RedisSearchCache(
    client=redis_client,
    key_builder=SearchCacheKeyBuilder(),
    ttl_seconds=SEARCH_CACHE_TTL_SECONDS,
)

search_service = SearchService(
    search_engine=search_engine,
    cache=search_cache,
)

indexing_service = IndexingService(search_engine)