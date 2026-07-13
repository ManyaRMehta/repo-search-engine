from sqlalchemy import select, update
from sqlalchemy.orm import Session

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