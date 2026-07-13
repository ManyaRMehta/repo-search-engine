from pathlib import Path

from app.services.search_engine import SearchEngine


def test_search_engine_indexes_repository(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text("jwt token validation", encoding="utf-8")
    (repo / "README.md").write_text("project documentation", encoding="utf-8")

    engine = SearchEngine()
    summary = engine.index_repository(repo)

    assert summary.files_indexed == 2
    assert summary.total_tokens > 0
    assert summary.indexed_extensions == [".md", ".py"]
    assert engine.total_documents() == 2


def test_search_engine_returns_ranked_results_after_indexing(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text(
        "jwt jwt jwt token validation",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        "jwt overview",
        encoding="utf-8",
    )

    engine = SearchEngine()
    engine.index_repository(repo)

    results = engine.search("jwt token")

    assert len(results) == 2
    assert results[0].relative_path == "auth.py"
    assert results[0].matched_tokens == ["jwt", "token"]


def test_search_engine_ignores_unsupported_files(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text("jwt token validation", encoding="utf-8")
    (repo / "logo.png").write_bytes(b"fake image bytes")

    engine = SearchEngine()
    summary = engine.index_repository(repo)

    assert summary.files_indexed == 1
    assert engine.total_documents() == 1


def test_search_engine_reindexing_replaces_previous_index(tmp_path: Path):
    first_repo = tmp_path / "first_repo"
    first_repo.mkdir()
    (first_repo / "auth.py").write_text("jwt token validation", encoding="utf-8")

    second_repo = tmp_path / "second_repo"
    second_repo.mkdir()
    (second_repo / "payments.py").write_text("stripe payment checkout", encoding="utf-8")

    engine = SearchEngine()

    engine.index_repository(first_repo)
    first_results = engine.search("jwt")

    assert len(first_results) == 1
    assert first_results[0].relative_path == "auth.py"

    engine.index_repository(second_repo)
    old_results = engine.search("jwt")
    new_results = engine.search("stripe")

    assert old_results == []
    assert len(new_results) == 1
    assert new_results[0].relative_path == "payments.py"


def test_search_engine_returns_empty_results_for_empty_query(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text("jwt token validation", encoding="utf-8")

    engine = SearchEngine()
    engine.index_repository(repo)

    results = engine.search("")

    assert results == []

def test_search_engine_returns_autocomplete_suggestions(tmp_path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "search.py").write_text(
        "class SearchEngine:\n"
        "    def search_repository(self):\n"
        "        searchable = True\n",
        encoding="utf-8",
    )

    engine = SearchEngine()
    engine.index_repository(repo)

    assert engine.suggest("search") == [
    "search",
    "search_repository",
    "searchable",
    "SearchEngine",
    ]

    assert engine.suggest("Search") == [
        "search",
        "search_repository",
        "searchable",
        "SearchEngine",
    ]