import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
import math
import statistics
from app.services.search_engine import SearchEngine
from collections.abc import Callable
from typing import Protocol
from app.services.redis_search_cache import RedisSearchCache
from app.services.search_cache_key import SearchCacheKeyBuilder
from app.services.search_service import SearchService


DEFAULT_QUERIES = [
    "repository crawler",
    "code tokenizer",
    "inverted index",
    "bm25 ranker",
    "search engine",
]

class BenchmarkRedisClient(Protocol):
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

    def delete(
        self,
        *keys: str,
    ) -> int:
        ...

@dataclass(frozen=True)
class QueryBenchmark:
    query: str
    latency_ms: float
    result_count: int

@dataclass(frozen=True)
class LatencyDistribution:
    median_ms: float
    p95_ms: float


@dataclass(frozen=True)
class CacheQueryBenchmark:
    query: str
    iterations: int
    raw_bm25: LatencyDistribution
    cache_miss: LatencyDistribution
    cache_hit: LatencyDistribution
    result_count: int

@dataclass(frozen=True)
class CacheBenchmarkReport:
    repo_path: str
    files_indexed: int
    total_tokens: int
    indexed_extensions: list[str]
    iterations: int
    queries: list[CacheQueryBenchmark]

@dataclass(frozen=True)
class BenchmarkReport:
    repo_path: str
    files_indexed: int
    total_tokens: int
    indexed_extensions: list[str]
    indexing_time_ms: float
    queries: list[QueryBenchmark]


def calculate_latency_distribution(
    latencies_ms: list[float],
) -> LatencyDistribution:
    if not latencies_ms:
        raise ValueError(
            "At least one latency measurement is required."
        )

    sorted_latencies = sorted(latencies_ms)

    percentile_rank = math.ceil(
        0.95 * len(sorted_latencies)
    )
    p95_index = percentile_rank - 1

    return LatencyDistribution(
        median_ms=round(
            statistics.median(sorted_latencies),
            3,
        ),
        p95_ms=round(
            sorted_latencies[p95_index],
            3,
        ),
    )


def measure_operation_latency(
    *,
    operation: Callable[[], object],
    iterations: int,
    timer: Callable[[], float] = time.perf_counter,
    before_each: Callable[[], object] | None = None,
) -> LatencyDistribution:
    if iterations <= 0:
        raise ValueError(
            "Benchmark iterations must be greater than zero."
        )

    latencies_ms: list[float] = []

    for _ in range(iterations):
        if before_each is not None:
            before_each()
        start_time = timer()
        operation()
        end_time = timer()

        latencies_ms.append(
            (end_time - start_time) * 1000
        )

    return calculate_latency_distribution(
        latencies_ms
    )

def run_cache_benchmark(
    *,
    repo_path: str | Path,
    queries: list[str],
    limit: int,
    iterations: int,
    redis_client: BenchmarkRedisClient,
    repository_id: int,
    index_version: int,
    ttl_seconds: int,
) -> CacheBenchmarkReport:
    if iterations <= 0:
        raise ValueError(
            "Benchmark iterations must be greater than zero."
        )

    resolved_repo_path = Path(repo_path).resolve()

    search_engine = SearchEngine()
    source_files = search_engine.crawler.crawl(
        resolved_repo_path
    )

    documents = [
        (document_id, source_file)
        for document_id, source_file in enumerate(
            source_files,
            start=1,
        )
    ]

    state = search_engine.build_runtime_state(
        repo_path=resolved_repo_path,
        documents=documents,
        repository_id=repository_id,
        index_version=index_version,
    )
    search_engine.activate_runtime_state(state)

    key_builder = SearchCacheKeyBuilder()

    cache = RedisSearchCache(
        client=redis_client,
        key_builder=key_builder,
        ttl_seconds=ttl_seconds,
    )

    search_service = SearchService(
        search_engine=search_engine,
        cache=cache,
    )

    query_reports: list[CacheQueryBenchmark] = []

    for query in queries:
        raw_results = search_engine.search_state(
            state,
            query=query,
            limit=limit,
        )

        raw_distribution = measure_operation_latency(
            operation=lambda query=query: (
                search_engine.search_state(
                    state,
                    query=query,
                    limit=limit,
                )
            ),
            iterations=iterations,
        )

        cache_key = key_builder.build(
            repository_id=repository_id,
            index_version=index_version,
            query=query,
            limit=limit,
        )

        miss_distribution = measure_operation_latency(
            operation=lambda query=query: (
                search_service.search(
                    query=query,
                    limit=limit,
                )
            ),
            iterations=iterations,
            before_each=lambda cache_key=cache_key: (
                redis_client.delete(cache_key)
            ),
        )

        redis_client.delete(cache_key)

        warmed_results = search_service.search(
            query=query,
            limit=limit,
        )

        if warmed_results != raw_results:
            raise RuntimeError(
                "Cached results differed from raw BM25 results."
            )

        hit_distribution = measure_operation_latency(
            operation=lambda query=query: (
                search_service.search(
                    query=query,
                    limit=limit,
                )
            ),
            iterations=iterations,
        )

        query_reports.append(
            CacheQueryBenchmark(
                query=query,
                iterations=iterations,
                raw_bm25=raw_distribution,
                cache_miss=miss_distribution,
                cache_hit=hit_distribution,
                result_count=len(raw_results),
            )
        )

    total_tokens = sum(
        document.total_tokens
        for document in state.index.documents.values()
    )

    indexed_extensions = sorted(
        {
            document.extension
            for document in state.index.documents.values()
        }
    )

    return CacheBenchmarkReport(
        repo_path=str(resolved_repo_path),
        files_indexed=len(documents),
        total_tokens=total_tokens,
        indexed_extensions=indexed_extensions,
        iterations=iterations,
        queries=query_reports,
    )

def run_benchmark(
    repo_path: str | Path,
    queries: list[str],
    limit: int,
) -> BenchmarkReport:
    engine = SearchEngine()

    indexing_start = time.perf_counter()
    summary = engine.index_repository(repo_path)
    indexing_end = time.perf_counter()

    query_benchmarks: list[QueryBenchmark] = []

    for query in queries:
        query_start = time.perf_counter()
        results = engine.search(query=query, limit=limit)
        query_end = time.perf_counter()

        query_benchmarks.append(
            QueryBenchmark(
                query=query,
                latency_ms=round((query_end - query_start) * 1000, 3),
                result_count=len(results),
            )
        )

    return BenchmarkReport(
        repo_path=summary.repo_path,
        files_indexed=summary.files_indexed,
        total_tokens=summary.total_tokens,
        indexed_extensions=summary.indexed_extensions,
        indexing_time_ms=round((indexing_end - indexing_start) * 1000, 3),
        queries=query_benchmarks,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark repository indexing and search latency."
    )

    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to the local repository to benchmark.",
    )

    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Search query to benchmark. Can be provided multiple times.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results per query.",
    )

    args = parser.parse_args()

    queries = args.queries or DEFAULT_QUERIES

    report = run_benchmark(
        repo_path=args.repo_path,
        queries=queries,
        limit=args.limit,
    )

    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()