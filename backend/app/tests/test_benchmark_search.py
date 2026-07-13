from pathlib import Path

from scripts.benchmark_search import run_benchmark


def test_benchmark_runner_reports_indexing_and_query_metrics(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text(
        "jwt token validation\n"
        "refresh jwt token\n",
        encoding="utf-8",
    )

    (repo / "search.py").write_text(
        "inverted index bm25 ranker\n",
        encoding="utf-8",
    )

    report = run_benchmark(
        repo_path=repo,
        queries=["jwt token", "bm25"],
        limit=5,
    )

    assert report.files_indexed == 2
    assert report.total_tokens > 0
    assert report.indexing_time_ms >= 0
    assert len(report.queries) == 2

    assert report.queries[0].query == "jwt token"
    assert report.queries[0].latency_ms >= 0
    assert report.queries[0].result_count >= 1

    assert report.queries[1].query == "bm25"
    assert report.queries[1].latency_ms >= 0
    assert report.queries[1].result_count >= 1