from pathlib import Path

from app.services.search_engine import SearchEngine
from app.models.source_file import SourceFile


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

def test_load_documents_uses_persisted_document_ids(
    tmp_path: Path,
) -> None:
    engine = SearchEngine()

    source_file = SourceFile(
        path=tmp_path / "search.py",
        relative_path="search.py",
        extension=".py",
        size_bytes=20,
        content="class SearchEngine:",
    )

    engine.load_documents(
        repo_path=tmp_path,
        documents=[(42, source_file)],
    )

    results = engine.search("SearchEngine")

    assert engine.total_documents() == 1
    assert engine.indexed_repo_path == tmp_path.resolve()
    assert results[0].document_id == 42
    suggestions = engine.suggest("Search")
    assert "search" in suggestions
    assert "SearchEngine" in suggestions


def test_build_runtime_state_does_not_replace_active_index(
    tmp_path: Path,
) -> None:
    engine = SearchEngine()

    active_content = "alphaexclusive"
    candidate_content = "betadistinct"

    active_file = SourceFile(
        path=tmp_path / "active.py",
        relative_path="active.py",
        extension=".py",
        size_bytes=len(active_content.encode("utf-8")),
        content=active_content,
    )

    candidate_file = SourceFile(
        path=tmp_path / "candidate.py",
        relative_path="candidate.py",
        extension=".py",
        size_bytes=len(candidate_content.encode("utf-8")),
        content=candidate_content,
    )

    engine.load_documents(
        repo_path=tmp_path / "active",
        documents=[(1, active_file)],
    )

    candidate_state = engine.build_runtime_state(
        repo_path=tmp_path / "candidate",
        documents=[(2, candidate_file)],
    )

    assert len(engine.search("alphaexclusive")) == 1
    assert engine.search("betadistinct") == []

    engine.activate_runtime_state(candidate_state)

    assert engine.search("alphaexclusive") == []

    candidate_results = engine.search("betadistinct")

    assert len(candidate_results) == 1
    assert candidate_results[0].document_id == 2

def test_build_runtime_state_preserves_repository_identity(
    tmp_path: Path,
) -> None:
    engine = SearchEngine()

    content = "searchable repository content"
    source_file = SourceFile(
        path=tmp_path / "search.py",
        relative_path="search.py",
        extension=".py",
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )

    state = engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(42, source_file)],
        repository_id=7,
        index_version=3,
    )

    assert state.repository_id == 7
    assert state.index_version == 3

def test_captured_runtime_state_remains_consistent_after_activation(
    tmp_path: Path,
) -> None:
    engine = SearchEngine()

    first_content = "alphaexclusive"
    first_file = SourceFile(
        path=tmp_path / "first.py",
        relative_path="first.py",
        extension=".py",
        size_bytes=len(first_content.encode("utf-8")),
        content=first_content,
    )

    second_content = "betadistinct"
    second_file = SourceFile(
        path=tmp_path / "second.py",
        relative_path="second.py",
        extension=".py",
        size_bytes=len(second_content.encode("utf-8")),
        content=second_content,
    )

    first_state = engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(1, first_file)],
        repository_id=7,
        index_version=1,
    )
    engine.activate_runtime_state(first_state)

    captured_state = engine.current_runtime_state()

    second_state = engine.build_runtime_state(
        repo_path=tmp_path,
        documents=[(2, second_file)],
        repository_id=7,
        index_version=2,
    )
    engine.activate_runtime_state(second_state)

    assert captured_state is first_state
    assert engine.current_runtime_state() is second_state

    #assert len(captured_state.ranker.search("alphaexclusive")) == 1
    #assert captured_state.ranker.search("betadistinct") == []
    assert len(
        engine.search_state(
            captured_state,
            query="alphaexclusive",
        )
    ) == 1

    assert engine.search_state(
        captured_state,
        query="betadistinct",
    ) == []
    assert engine.search("alphaexclusive") == []
    assert len(engine.search("betadistinct")) == 1