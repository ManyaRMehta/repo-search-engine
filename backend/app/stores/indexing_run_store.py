from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.records import IndexingRunRecord


class IndexingRunStore:
    """Handles persistence operations for repository indexing attempts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        repository_id: int,
    ) -> IndexingRunRecord:
        indexing_run = IndexingRunRecord(
            repository_id=repository_id,
        )

        self.session.add(indexing_run)
        self.session.flush()

        return indexing_run

    def mark_succeeded(
        self,
        indexing_run: IndexingRunRecord,
        *,
        files_discovered: int,
        files_indexed: int,
        files_updated: int,
        files_deleted: int,
        total_tokens: int,
    ) -> IndexingRunRecord:
        indexing_run.status = "succeeded"
        indexing_run.completed_at = datetime.now(timezone.utc)
        indexing_run.files_discovered = files_discovered
        indexing_run.files_indexed = files_indexed
        indexing_run.files_updated = files_updated
        indexing_run.files_deleted = files_deleted
        indexing_run.total_tokens = total_tokens
        indexing_run.error_message = None

        self.session.flush()

        return indexing_run

    def mark_failed(
        self,
        indexing_run: IndexingRunRecord,
        error_message: str,
    ) -> IndexingRunRecord:
        indexing_run.status = "failed"
        indexing_run.completed_at = datetime.now(timezone.utc)
        indexing_run.error_message = error_message

        self.session.flush()

        return indexing_run