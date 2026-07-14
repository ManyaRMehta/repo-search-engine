from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.source_file import SourceFile
from app.stores.document_store import DocumentStore
from app.stores.repository_store import RepositoryStore

pytestmark = pytest.mark.postgres_integration

def make_source_file(
    relative_path: str,
    content: str,
) -> SourceFile:
    return SourceFile(
        path=Path("/tmp/repository") / relative_path,
        relative_path=relative_path,
        extension=Path(relative_path).suffix,
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )


def create_repository(database_session: Session) -> int:
    repository = RepositoryStore(database_session).create(
        name="sample-repository",
        canonical_path="/tmp/sample-repository",
    )

    return repository.id


def test_synchronize_creates_documents(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = DocumentStore(database_session)

    summary = store.synchronize(
        repository_id,
        [
            make_source_file("app/main.py", "print('hello')"),
            make_source_file("README.md", "# Sample"),
        ],
    )

    documents = store.list_by_repository(repository_id)

    assert summary.files_created == 2
    assert summary.files_updated == 0
    assert summary.files_deleted == 0
    assert summary.files_unchanged == 0
    assert summary.files_discovered == 2

    assert len(documents) == 2
    assert {
        document.relative_path
        for document in documents
    } == {
        "README.md",
        "app/main.py",
}


def test_synchronize_preserves_id_for_unchanged_document(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = DocumentStore(database_session)

    source_file = make_source_file(
        "app/main.py",
        "print('hello')",
    )

    store.synchronize(repository_id, [source_file])
    original_document = store.list_by_repository(repository_id)[0]
    original_document_id = original_document.id

    summary = store.synchronize(repository_id, [source_file])
    persisted_document = store.list_by_repository(repository_id)[0]

    assert summary.files_created == 0
    assert summary.files_updated == 0
    assert summary.files_deleted == 0
    assert summary.files_unchanged == 1
    assert persisted_document.id == original_document_id


def test_synchronize_updates_document_without_changing_id(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = DocumentStore(database_session)

    store.synchronize(
        repository_id,
        [make_source_file("app/main.py", "first")],
    )

    original_document = store.list_by_repository(repository_id)[0]
    original_document_id = original_document.id
    original_hash = original_document.content_hash

    summary = store.synchronize(
        repository_id,
        [make_source_file("app/main.py", "other")],
    )

    updated_document = store.list_by_repository(repository_id)[0]

    assert summary.files_created == 0
    assert summary.files_updated == 1
    assert summary.files_deleted == 0
    assert summary.files_unchanged == 0

    assert updated_document.id == original_document_id
    assert updated_document.content == "other"
    assert updated_document.content_hash != original_hash


def test_synchronize_deletes_documents_missing_from_snapshot(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = DocumentStore(database_session)

    store.synchronize(
        repository_id,
        [
            make_source_file("app/main.py", "main"),
            make_source_file("app/routes.py", "routes"),
        ],
    )

    summary = store.synchronize(
        repository_id,
        [
            make_source_file("app/main.py", "main"),
        ],
    )

    remaining_documents = store.list_by_repository(repository_id)

    assert summary.files_created == 0
    assert summary.files_updated == 0
    assert summary.files_deleted == 1
    assert summary.files_unchanged == 1

    assert len(remaining_documents) == 1
    assert remaining_documents[0].relative_path == "app/main.py"


def test_synchronize_rejects_duplicate_relative_paths(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = DocumentStore(database_session)

    duplicate_files = [
        make_source_file("app/main.py", "first"),
        make_source_file("app/main.py", "second"),
    ]

    with pytest.raises(
        ValueError,
        match="Duplicate relative path",
    ):
        store.synchronize(repository_id, duplicate_files)