from sqlalchemy.orm import Session

from app.stores.indexing_run_store import IndexingRunStore
from app.stores.repository_store import RepositoryStore


def create_repository(database_session: Session) -> int:
    repository = RepositoryStore(database_session).create(
        name="sample-repository",
        canonical_path="/tmp/indexing-run-repository",
    )

    return repository.id


def test_create_indexing_run(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = IndexingRunStore(database_session)

    indexing_run = store.create(repository_id)

    assert indexing_run.id is not None
    assert indexing_run.repository_id == repository_id
    assert indexing_run.status == "running"
    assert indexing_run.completed_at is None


def test_mark_indexing_run_succeeded(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = IndexingRunStore(database_session)
    indexing_run = store.create(repository_id)

    store.mark_succeeded(
        indexing_run,
        files_discovered=5,
        files_indexed=5,
        files_updated=2,
        files_deleted=1,
        total_tokens=120,
    )

    assert indexing_run.status == "succeeded"
    assert indexing_run.completed_at is not None
    assert indexing_run.files_discovered == 5
    assert indexing_run.files_indexed == 5
    assert indexing_run.files_updated == 2
    assert indexing_run.files_deleted == 1
    assert indexing_run.total_tokens == 120
    assert indexing_run.error_message is None


def test_mark_indexing_run_failed(
    database_session: Session,
) -> None:
    repository_id = create_repository(database_session)
    store = IndexingRunStore(database_session)
    indexing_run = store.create(repository_id)

    store.mark_failed(
        indexing_run,
        error_message="Repository could not be read",
    )

    assert indexing_run.status == "failed"
    assert indexing_run.completed_at is not None
    assert indexing_run.error_message == "Repository could not be read"

def test_get_indexing_run_by_id(
    database_session: Session,
) -> None:
    repository = RepositoryStore(database_session).create(
        name="sample",
        canonical_path="/tmp/get-run-by-id-sample",
    )

    store = IndexingRunStore(database_session)
    indexing_run = store.create(repository.id)

    found_run = store.get_by_id(indexing_run.id)

    assert found_run is not None
    assert found_run.id == indexing_run.id