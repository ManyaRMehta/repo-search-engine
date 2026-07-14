import pytest
from sqlalchemy.orm import Session

from app.stores.repository_store import RepositoryStore


pytestmark = pytest.mark.postgres_integration

def test_create_and_find_repository(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    created_repository = store.create(
        name="sample-repository",
        canonical_path="/tmp/sample-repository",
    )

    found_repository = store.get_by_canonical_path(
        "/tmp/sample-repository"
    )

    assert created_repository.id is not None
    assert found_repository is not None
    assert found_repository.id == created_repository.id
    assert found_repository.name == "sample-repository"
    assert found_repository.status == "indexing"
    assert found_repository.index_version == 0


def test_setting_active_repository_deactivates_previous_repository(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    first_repository = store.create(
        name="first-repository",
        canonical_path="/tmp/first-repository",
    )
    second_repository = store.create(
        name="second-repository",
        canonical_path="/tmp/second-repository",
    )

    store.set_active(first_repository.id)
    store.set_active(second_repository.id)

    active_repository = store.get_active()

    assert active_repository is not None
    assert active_repository.id == second_repository.id

    database_session.refresh(first_repository)
    assert first_repository.is_active is False


def test_set_active_returns_none_for_missing_repository(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    result = store.set_active(repository_id=999_999)

    assert result is None

def test_get_or_create_returns_existing_repository(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    created_repository, was_created = store.get_or_create(
        name="sample",
        canonical_path="/tmp/sample",
    )

    found_repository, was_created_again = store.get_or_create(
        name="different-name",
        canonical_path="/tmp/sample",
    )

    assert was_created is True
    assert was_created_again is False
    assert found_repository.id == created_repository.id
    assert found_repository.name == "sample"

def test_repository_lifecycle_updates_status_and_version(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    repository = store.create(
        name="sample",
        canonical_path="/tmp/lifecycle-sample",
    )

    store.mark_indexing(repository)

    assert repository.status == "indexing"
    assert repository.index_version == 0

    store.mark_ready(repository)

    assert repository.status == "ready"
    assert repository.index_version == 1
    assert repository.last_indexed_at is not None

    store.mark_failed(repository)

    assert repository.status == "failed"
    assert repository.index_version == 1

def test_get_repository_by_id(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    repository = store.create(
        name="sample",
        canonical_path="/tmp/get-by-id-sample",
    )

    found_repository = store.get_by_id(repository.id)

    assert found_repository is not None
    assert found_repository.id == repository.id

def test_failed_reindex_preserves_previous_ready_version(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    repository = store.create(
        name="sample",
        canonical_path="/tmp/failed-reindex-sample",
    )

    store.mark_ready(repository)
    store.mark_indexing(repository)
    store.mark_indexing_failed(repository)

    assert repository.status == "ready"
    assert repository.index_version == 1

def test_failed_initial_index_marks_repository_failed(
    database_session: Session,
) -> None:
    store = RepositoryStore(database_session)

    repository = store.create(
        name="sample",
        canonical_path="/tmp/failed-initial-index-sample",
    )

    store.mark_indexing_failed(repository)

    assert repository.status == "failed"
    assert repository.index_version == 0