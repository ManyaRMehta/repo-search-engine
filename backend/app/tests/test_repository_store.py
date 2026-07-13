from sqlalchemy.orm import Session

from app.stores.repository_store import RepositoryStore


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