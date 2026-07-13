from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.records import DocumentRecord
from app.models.source_file import SourceFile
from app.services.search_engine import SearchEngine
from app.stores.document_store import DocumentStore
from app.stores.repository_store import RepositoryStore


SessionFactory = Callable[[], AbstractContextManager[Session]]


class IndexingService:
    """Coordinates persisted documents and runtime search state."""

    def __init__(
        self,
        search_engine: SearchEngine,
        session_factory: SessionFactory = SessionLocal,
    ) -> None:
        self.search_engine = search_engine
        self.session_factory = session_factory

    def hydrate_active_repository(self) -> bool:
        with self.session_factory() as session:
            repository = RepositoryStore(session).get_active()

            if repository is None or repository.status != "ready":
                return False

            repository_path = repository.canonical_path
            document_records = DocumentStore(
                session
            ).list_by_repository(repository.id)

            documents = [
                (
                    document.id,
                    self._to_source_file(
                        repository_path,
                        document,
                    ),
                )
                for document in document_records
            ]

        candidate_state = self.search_engine.build_runtime_state(
            repo_path=repository_path,
            documents=documents,
        )

        self.search_engine.activate_runtime_state(candidate_state)

        return True

    @staticmethod
    def _to_source_file(
        repository_path: str,
        document: DocumentRecord,
    ) -> SourceFile:
        return SourceFile(
            path=Path(repository_path) / document.relative_path,
            relative_path=document.relative_path,
            extension=document.extension,
            size_bytes=document.size_bytes,
            content=document.content,
        )