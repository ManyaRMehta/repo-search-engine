from sqlalchemy import select, update
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database.records import RepositoryRecord


class RepositoryStore:
    """Handles persistence operations for repositories."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_canonical_path(
        self,
        canonical_path: str,
    ) -> RepositoryRecord | None:
        statement = select(RepositoryRecord).where(
            RepositoryRecord.canonical_path == canonical_path
        )

        return self.session.scalar(statement)

    def get_active(self) -> RepositoryRecord | None:
        statement = select(RepositoryRecord).where(
            RepositoryRecord.is_active.is_(True)
        )

        return self.session.scalar(statement)

    def create(
        self,
        *,
        name: str,
        canonical_path: str,
    ) -> RepositoryRecord:
        repository = RepositoryRecord(
            name=name,
            canonical_path=canonical_path,
        )

        self.session.add(repository)
        self.session.flush()

        return repository

    def set_active(
        self,
        repository_id: int,
    ) -> RepositoryRecord | None:
        repository = self.session.get(
            RepositoryRecord,
            repository_id,
        )

        if repository is None:
            return None

        self.session.execute(
            update(RepositoryRecord).values(is_active=False)
        )

        repository.is_active = True
        self.session.flush()

        return repository
    
    def get_or_create(
        self,
        *,
        name: str,
        canonical_path: str,
    ) -> tuple[RepositoryRecord, bool]:
        repository = self.get_by_canonical_path(canonical_path)

        if repository is not None:
            return repository, False

        return (
            self.create(
                name=name,
                canonical_path=canonical_path,
            ),
            True,
        )

    def mark_indexing(
        self,
        repository: RepositoryRecord,
    ) -> RepositoryRecord:
        repository.status = "indexing"
        self.session.flush()

        return repository

    def mark_ready(
        self,
        repository: RepositoryRecord,
    ) -> RepositoryRecord:
        repository.status = "ready"
        repository.index_version += 1
        repository.last_indexed_at = datetime.now(timezone.utc)

        self.session.flush()

        return repository

    def mark_failed(
        self,
        repository: RepositoryRecord,
    ) -> RepositoryRecord:
        repository.status = "failed"
        self.session.flush()

        return repository
    
    def get_by_id(
        self,
        repository_id: int,
    ) -> RepositoryRecord | None:
        return self.session.get(
            RepositoryRecord,
            repository_id,
        )
    
    def mark_indexing_failed(
        self,
        repository: RepositoryRecord,
    ) -> RepositoryRecord:
        if repository.index_version > 0:
            repository.status = "ready"
        else:
            repository.status = "failed"

        self.session.flush()

        return repository