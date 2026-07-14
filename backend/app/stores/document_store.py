import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.records import DocumentRecord
from app.models.document_sync_summary import DocumentSyncSummary
from app.models.source_file import SourceFile


class DocumentStore:
    """Synchronizes persisted documents with a crawled repository snapshot."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_repository(
        self,
        repository_id: int,
    ) -> list[DocumentRecord]:
        statement = (
            select(DocumentRecord)
            .where(DocumentRecord.repository_id == repository_id)
            .order_by(DocumentRecord.relative_path)
        )

        return list(self.session.scalars(statement))

    def synchronize(
        self,
        repository_id: int,
        source_files: list[SourceFile],
    ) -> DocumentSyncSummary:
        existing_documents = self.list_by_repository(repository_id)

        existing_by_path = {
            document.relative_path: document
            for document in existing_documents
        }

        seen_paths: set[str] = set()

        files_created = 0
        files_updated = 0
        files_unchanged = 0

        for source_file in source_files:
            if source_file.relative_path in seen_paths:
                raise ValueError(
                    "Duplicate relative path in repository snapshot: "
                    f"{source_file.relative_path}"
                )

            seen_paths.add(source_file.relative_path)

            content_hash = self._hash_content(source_file.content)
            line_count = len(source_file.content.splitlines())

            existing_document = existing_by_path.get(
                source_file.relative_path
            )

            if existing_document is None:
                self.session.add(
                    DocumentRecord(
                        repository_id=repository_id,
                        relative_path=source_file.relative_path,
                        extension=source_file.extension,
                        size_bytes=source_file.size_bytes,
                        line_count=line_count,
                        content=source_file.content,
                        content_hash=content_hash,
                    )
                )
                files_created += 1
                continue

            if self._matches_source(
                existing_document,
                source_file,
                content_hash,
                line_count,
            ):
                files_unchanged += 1
                continue

            existing_document.extension = source_file.extension
            existing_document.size_bytes = source_file.size_bytes
            existing_document.line_count = line_count
            existing_document.content = source_file.content
            existing_document.content_hash = content_hash

            files_updated += 1

        documents_to_delete = [
            document
            for relative_path, document in existing_by_path.items()
            if relative_path not in seen_paths
        ]

        for document in documents_to_delete:
            self.session.delete(document)

        self.session.flush()

        return DocumentSyncSummary(
            files_created=files_created,
            files_updated=files_updated,
            files_deleted=len(documents_to_delete),
            files_unchanged=files_unchanged,
        )

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _matches_source(
        document: DocumentRecord,
        source_file: SourceFile,
        content_hash: str,
        line_count: int,
    ) -> bool:
        return (
            document.content_hash == content_hash
            and document.extension == source_file.extension
            and document.size_bytes == source_file.size_bytes
            and document.line_count == line_count
        )