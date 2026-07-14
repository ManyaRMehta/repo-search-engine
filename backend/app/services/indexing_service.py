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
from app.models.indexing_summary import IndexingSummary
from app.services.repository_crawler import RepositoryCrawler
from app.stores.indexing_run_store import IndexingRunStore


SessionFactory = Callable[[], AbstractContextManager[Session]]

class NoIndexableFilesError(ValueError):
        """Raised when a repository contains no supported source files."""

class IndexingService:
    """Coordinates persisted documents and runtime search state."""

    def __init__(
        self,
        search_engine: SearchEngine,
        session_factory: SessionFactory = SessionLocal,
        crawler: RepositoryCrawler | None = None,
    ) -> None:
        self.search_engine = search_engine
        self.session_factory = session_factory
        self.crawler = crawler or RepositoryCrawler()

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
            repository_id=repository.id,
            index_version=repository.index_version,
        )

        self.search_engine.activate_runtime_state(candidate_state)

        return True

    def index_repository(
        self,
        repo_path: str | Path,
    ) -> IndexingSummary:
        resolved_repo_path = Path(repo_path).resolve()

        repository_id, indexing_run_id = self._start_indexing(
            resolved_repo_path
        )

        try:
            source_files = self.crawler.crawl(resolved_repo_path)

            if not source_files:
                raise NoIndexableFilesError(
                    "No supported source files were found to index."
                )

            with self.session_factory() as session:
                repository_store = RepositoryStore(session)
                document_store = DocumentStore(session)
                indexing_run_store = IndexingRunStore(session)

                repository = repository_store.get_by_id(repository_id)
                indexing_run = indexing_run_store.get_by_id(
                    indexing_run_id
                )

                if repository is None:
                    raise RuntimeError(
                        "Repository disappeared during indexing."
                    )

                if indexing_run is None:
                    raise RuntimeError(
                        "Indexing run disappeared during indexing."
                    )

                sync_summary = document_store.synchronize(
                    repository.id,
                    source_files,
                )

                document_records = document_store.list_by_repository(
                    repository.id
                )

                documents = [
                    (
                    document.id,
                        self._to_source_file(
                            repository.canonical_path,
                            document,
                        ),
                    )
                    for document in document_records
                ]

                #candidate_state = (
                #    self.search_engine.build_runtime_state(
                #        repo_path=repository.canonical_path,
                #        documents=documents,
                #    )
                #)

                repository_store.mark_ready(repository)

                candidate_state = self.search_engine.build_runtime_state(
                    repo_path=repository.canonical_path,
                    documents=documents,
                    repository_id=repository.id,
                    index_version=repository.index_version,
                )

                total_tokens = sum(
                    document.total_tokens
                    for document in candidate_state.index.documents.values()
                )

                indexed_extensions = sorted(
                    {
                        document.extension
                        for document
                        in candidate_state.index.documents.values()
                    }
                )


                #repository_store.set_active(repository.id)


                repository_store.set_active(repository.id)
                indexing_run_store.mark_succeeded(
                    indexing_run,
                    files_discovered=sync_summary.files_discovered,
                    files_indexed=len(documents),
                    files_updated=sync_summary.files_updated,
                    files_deleted=sync_summary.files_deleted,
                    total_tokens=total_tokens,
                )

                session.commit()

            self.search_engine.activate_runtime_state(
                candidate_state
            )

            return IndexingSummary(
                repo_path=str(resolved_repo_path),
                files_indexed=len(documents),
                total_tokens=total_tokens,
                indexed_extensions=indexed_extensions,
            )

        except Exception as error:
            self._record_indexing_failure(
                repository_id=repository_id,
                indexing_run_id=indexing_run_id,
                error_message=str(error),
            )
            raise

    def _start_indexing(
        self,
        repository_path: Path,
    ) -> tuple[int, int]:
        with self.session_factory() as session:
            repository_store = RepositoryStore(session)
            indexing_run_store = IndexingRunStore(session)

            repository, _ = repository_store.get_or_create(
                name=repository_path.name,
                canonical_path=str(repository_path),
            )

            repository_store.mark_indexing(repository)

            indexing_run = indexing_run_store.create(
                repository.id
            )

            session.commit()

            return repository.id, indexing_run.id


    def _record_indexing_failure(
        self,
        *,
        repository_id: int,
        indexing_run_id: int,
        error_message: str,
    ) -> None:
        with self.session_factory() as session:
            repository_store = RepositoryStore(session)
            indexing_run_store = IndexingRunStore(session)

            repository = repository_store.get_by_id(repository_id)
            indexing_run = indexing_run_store.get_by_id(
                indexing_run_id
            )

            if repository is not None:
                repository_store.mark_indexing_failed(repository)

            if indexing_run is not None:
                indexing_run_store.mark_failed(
                    indexing_run,
                    error_message=error_message,
                )

            session.commit()

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

