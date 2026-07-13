import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import sessionmaker

from app.database.records import (
    DocumentRecord,
    IndexingRunRecord,
    RepositoryRecord,
)


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://repo_search:repo_search"
    "@localhost:5433/repo_search_engine_test"
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    DEFAULT_TEST_DATABASE_URL,
)

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)

SessionFactory = Callable[[], AbstractContextManager[Session]]


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
    )

    session.execute(delete(IndexingRunRecord))
    session.execute(delete(DocumentRecord))
    session.execute(delete(RepositoryRecord))
    session.flush()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def database_session_factory(
) -> Generator[SessionFactory, None, None]:
    def clear_database() -> None:
        with TestSessionLocal() as session:
            session.execute(delete(IndexingRunRecord))
            session.execute(delete(DocumentRecord))
            session.execute(delete(RepositoryRecord))
            session.commit()

    clear_database()

    try:
        yield TestSessionLocal
    finally:
        clear_database()