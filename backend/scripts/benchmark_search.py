import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.services.search_engine import SearchEngine


DEFAULT_QUERIES = [
    "repository crawler",
    "code tokenizer",
    "inverted index",
    "bm25 ranker",
    "search engine",
]


@dataclass(frozen=True)
class QueryBenchmark:
    query: str
    latency_ms: float
    result_count: int


@dataclass(frozen=True)
class BenchmarkReport:
    repo_path: str
    files_indexed: int
    total_tokens: int
    indexed_extensions: list[str]
    indexing_time_ms: float
    queries: list[QueryBenchmark]


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