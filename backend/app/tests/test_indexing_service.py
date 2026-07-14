from contextlib import nullcontext
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.source_file import SourceFile
from app.services.indexing_service import IndexingService
from app.services.search_engine import SearchEngine
from app.stores.document_store import DocumentStore
from app.stores.repository_store import RepositoryStore
import pytest
from sqlalchemy import select

from app.database.records import (
    DocumentRecord,
    IndexingRunRecord,
    RepositoryRecord,
)
from app.services.runtime_search_state import RuntimeSearchState


def test_hydrate_active_repository_restores_runtime_index(
    database_session: Session,
) -> None:
    repository_store = RepositoryStore(database_session)

    repository = repository_store.create(
        name="sample-repository",
        canonical_path="/tmp/sample-repository",
    )

    source_file = SourceFile(
        path=Path("/tmp/sample-repository/app/search.py"),
        relative_path="app/search.py",
        extension=".py",
        size_bytes=len("class SearchEngine:".encode("utf-8")),
        content="class SearchEngine:",
    )

    DocumentStore(database_session).synchronize(
        repository.id,
        [source_file],
    )

    persisted_document = DocumentStore(
        database_session
    ).list_by_repository(repository.id)[0]

    repository_store.mark_ready(repository)
    repository_store.set_active(repository.id)

    search_engine = SearchEngine()

    indexing_service = IndexingService(
        search_engine,
        session_factory=lambda: nullcontext(database_session),
    )

    was_hydrated = indexing_service.hydrate_active_repository()
    runtime_state = search_engine.current_runtime_state()

    results = search_engine.search("SearchEngine")
    suggestions = search_engine.suggest("Search")

    assert was_hydrated is True
    assert search_engine.total_documents() == 1
    assert results[0].document_id == persisted_document.id
    assert results[0].relative_path == "app/search.py"
    assert "SearchEngine" in suggestions
    assert runtime_state.repository_id == repository.id
    assert runtime_state.index_version == repository.index_version

def test_index_repository_persists_and_activates_repository(
    tmp_path: Path,
    database_session_factory,
) -> None:
    repo_path = tmp_path / "sample-repository"
    repo_path.mkdir()

    source_path = repo_path / "search.py"
    source_path.write_text(
        "class PersistentSearchEngine:",
        encoding="utf-8",
    )

    search_engine = SearchEngine()
    service = IndexingService(
        search_engine,
        session_factory=database_session_factory,
    )

    summary = service.index_repository(repo_path)
    results = search_engine.search("PersistentSearchEngine")
    runtime_state = search_engine.current_runtime_state()

    assert summary.files_indexed == 1
    assert search_engine.total_documents() == 1
    assert len(results) == 1

    with database_session_factory() as session:
        repository = session.scalar(
            select(RepositoryRecord).where(
                RepositoryRecord.canonical_path
                == str(repo_path.resolve())
            )
        )

        assert repository is not None
        assert runtime_state.repository_id == repository.id
        assert runtime_state.index_version == repository.index_version

        documents = list(
            session.scalars(
                select(DocumentRecord).where(
                    DocumentRecord.repository_id
                    == repository.id
                )
            )
        )

        indexing_runs = list(
            session.scalars(
                select(IndexingRunRecord).where(
                    IndexingRunRecord.repository_id
                    == repository.id
                )
            )
        )

        assert repository.status == "ready"
        assert repository.is_active is True
        assert repository.index_version == 1

        assert len(documents) == 1
        assert results[0].document_id == documents[0].id

        assert len(indexing_runs) == 1
        assert indexing_runs[0].status == "succeeded"

def test_reindex_updates_document_and_preserves_id(
    tmp_path: Path,
    database_session_factory,
) -> None:
    repo_path = tmp_path / "sample-repository"
    repo_path.mkdir()

    source_path = repo_path / "search.py"
    source_path.write_text(
        "firstexclusive",
        encoding="utf-8",
    )

    search_engine = SearchEngine()
    service = IndexingService(
        search_engine,
        session_factory=database_session_factory,
    )

    service.index_repository(repo_path)

    original_result = search_engine.search(
        "firstexclusive"
    )[0]
    original_document_id = original_result.document_id

    source_path.write_text(
        "secondexclusive",
        encoding="utf-8",
    )

    service.index_repository(repo_path)

    updated_results = search_engine.search(
        "secondexclusive"
    )

    assert search_engine.search("firstexclusive") == []
    assert len(updated_results) == 1
    assert (
        updated_results[0].document_id
        == original_document_id
    )

    with database_session_factory() as session:
        repository = session.scalar(
            select(RepositoryRecord).where(
                RepositoryRecord.canonical_path
                == str(repo_path.resolve())
            )
        )

        assert repository is not None
        assert repository.status == "ready"
        assert repository.index_version == 2

        documents = list(
            session.scalars(
                select(DocumentRecord).where(
                    DocumentRecord.repository_id
                    == repository.id
                )
            )
        )

        indexing_runs = list(
            session.scalars(
                select(IndexingRunRecord).where(
                    IndexingRunRecord.repository_id
                    == repository.id
                )
            )
        )

        assert len(documents) == 1
        assert documents[0].id == original_document_id
        assert documents[0].content == "secondexclusive"

        assert len(indexing_runs) == 2
        assert all(
            run.status == "succeeded"
            for run in indexing_runs
        )

def test_failed_reindex_preserves_database_and_runtime_state(
    tmp_path: Path,
    database_session_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_path = tmp_path / "sample-repository"
    repo_path.mkdir()

    source_path = repo_path / "search.py"
    source_path.write_text(
        "stableexclusive",
        encoding="utf-8",
    )

    search_engine = SearchEngine()
    service = IndexingService(
        search_engine,
        session_factory=database_session_factory,
    )

    service.index_repository(repo_path)

    stable_result = search_engine.search(
        "stableexclusive"
    )[0]
    stable_document_id = stable_result.document_id

    source_path.write_text(
        "failedreplacement",
        encoding="utf-8",
    )

    def fail_runtime_build(
        repo_path: str | Path,
        documents: list[tuple[int, SourceFile]],
        repository_id: int | None = None,
        index_version: int | None = None,
    ) -> RuntimeSearchState:
        raise RuntimeError("runtime build failed")

    monkeypatch.setattr(
        search_engine,
        "build_runtime_state",
        fail_runtime_build,
    )

    with pytest.raises(
        RuntimeError,
        match="runtime build failed",
    ):
        service.index_repository(repo_path)

    assert (
        search_engine.search("stableexclusive")[0].document_id
        == stable_document_id
    )
    assert search_engine.search("failedreplacement") == []

    with database_session_factory() as session:
        repository = session.scalar(
            select(RepositoryRecord).where(
                RepositoryRecord.canonical_path
                == str(repo_path.resolve())
            )
        )

        assert repository is not None
        assert repository.status == "ready"
        assert repository.index_version == 1

        documents = list(
            session.scalars(
                select(DocumentRecord).where(
                    DocumentRecord.repository_id
                    == repository.id
                )
            )
        )

        indexing_runs = list(
            session.scalars(
                select(IndexingRunRecord)
                .where(
                    IndexingRunRecord.repository_id
                    == repository.id
                )
                .order_by(IndexingRunRecord.id)
            )
        )

        assert len(documents) == 1
        assert documents[0].id == stable_document_id
        assert documents[0].content == "stableexclusive"

        assert [
            run.status
            for run in indexing_runs
        ] == [
            "succeeded",
            "failed",
        ]