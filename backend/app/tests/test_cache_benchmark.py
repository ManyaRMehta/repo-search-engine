from scripts.benchmark_search import (
    CacheBenchmarkReport,
    CacheQueryBenchmark,
    LatencyDistribution,
    calculate_latency_distribution,
    measure_operation_latency,
    run_cache_benchmark,
)


def test_cache_benchmark_report_represents_all_search_paths() -> None:
    report = CacheQueryBenchmark(
        query="jwt token",
        iterations=100,
        raw_bm25=LatencyDistribution(
            median_ms=0.2,
            p95_ms=0.3,
        ),
        cache_miss=LatencyDistribution(
            median_ms=1.2,
            p95_ms=1.5,
        ),
        cache_hit=LatencyDistribution(
            median_ms=0.4,
            p95_ms=0.6,
        ),
        result_count=2,
    )

    assert report.query == "jwt token"
    assert report.iterations == 100
    assert report.raw_bm25.median_ms == 0.2
    assert report.cache_miss.median_ms == 1.2
    assert report.cache_hit.median_ms == 0.4
    assert report.result_count == 2

def test_calculate_latency_distribution_reports_median_and_p95() -> None:
    distribution = calculate_latency_distribution(
        [1.0, 5.0, 2.0, 4.0, 3.0]
    )

    assert distribution.median_ms == 3.0
    assert distribution.p95_ms == 5.0

def test_measure_operation_latency_uses_all_iterations() -> None:
    timer_values = iter(
        [
            0.000,
            0.001,
            0.010,
            0.013,
            0.020,
            0.025,
        ]
    )

    operation_calls = 0

    def fake_timer() -> float:
        return next(timer_values)

    def operation() -> None:
        nonlocal operation_calls
        operation_calls += 1

    distribution = measure_operation_latency(
        operation=operation,
        iterations=3,
        timer=fake_timer,
    )

    assert operation_calls == 3
    assert distribution.median_ms == 3.0
    assert distribution.p95_ms == 5.0

def test_measure_operation_latency_runs_setup_before_timing() -> None:
    events: list[str] = []
    timer_values = iter(
        [
            0.000,
            0.001,
            0.010,
            0.012,
        ]
    )

    def fake_timer() -> float:
        events.append("timer")
        return next(timer_values)

    def before_each() -> None:
        events.append("setup")

    def operation() -> None:
        events.append("operation")

    distribution = measure_operation_latency(
        operation=operation,
        iterations=2,
        timer=fake_timer,
        before_each=before_each,
    )

    assert events == [
        "setup",
        "timer",
        "operation",
        "timer",
        "setup",
        "timer",
        "operation",
        "timer",
    ]

    assert distribution.median_ms == 1.5
    assert distribution.p95_ms == 2.0

class FakeBenchmarkRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

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
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0

        for key in keys:
            if key in self.values:
                del self.values[key]
                deleted += 1

        return deleted
    
def test_run_cache_benchmark_reports_all_search_paths(
    tmp_path,
) -> None:
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text(
        "jwt token validation\n",
        encoding="utf-8",
    )

    (repo / "search.py").write_text(
        "inverted index bm25 ranker\n",
        encoding="utf-8",
    )

    report = run_cache_benchmark(
        repo_path=repo,
        queries=["jwt token"],
        limit=5,
        iterations=3,
        redis_client=FakeBenchmarkRedisClient(),
        repository_id=7,
        index_version=3,
        ttl_seconds=900,
    )

    assert isinstance(report, CacheBenchmarkReport)
    assert report.files_indexed == 2
    assert report.total_tokens > 0
    assert report.iterations == 3
    assert len(report.queries) == 1

    query_report = report.queries[0]

    assert query_report.query == "jwt token"
    assert query_report.iterations == 3
    assert query_report.result_count == 1

    assert query_report.raw_bm25.median_ms >= 0
    assert query_report.raw_bm25.p95_ms >= 0

    assert query_report.cache_miss.median_ms >= 0
    assert query_report.cache_miss.p95_ms >= 0

    assert query_report.cache_hit.median_ms >= 0
    assert query_report.cache_hit.p95_ms >= 0