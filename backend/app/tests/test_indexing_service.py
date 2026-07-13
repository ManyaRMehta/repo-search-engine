from contextlib import nullcontext
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.source_file import SourceFile
from app.services.indexing_service import IndexingService
from app.services.search_engine import SearchEngine
from app.stores.document_store import DocumentStore
from app.stores.repository_store import RepositoryStore


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

    results = search_engine.search("SearchEngine")
    suggestions = search_engine.suggest("Search")

    assert was_hydrated is True
    assert search_engine.total_documents() == 1
    assert results[0].document_id == persisted_document.id
    assert results[0].relative_path == "app/search.py"
    assert "SearchEngine" in suggestions