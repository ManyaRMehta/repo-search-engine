from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.runtime import indexing_service, search_engine


@pytest.fixture(autouse=True)
def configure_test_runtime(
    database_session_factory,
) -> Generator[None, None, None]:
    original_session_factory = indexing_service.session_factory

    indexing_service.session_factory = database_session_factory
    search_engine.reset()

    try:
        yield
    finally:
        search_engine.reset()
        indexing_service.session_factory = original_session_factory


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "indexed_documents" in response.json()


def test_index_repository_and_search(client: TestClient,tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text(
        "def validateJwtToken():\n"
        "    return 'jwt token valid'\n",
        encoding="utf-8",
    )

    (repo / "README.md").write_text(
        "This project handles authentication.",
        encoding="utf-8",
    )

    index_response = client.post(
        "/index",
        json={"repo_path": str(repo)},
    )

    assert index_response.status_code == 200

    index_data = index_response.json()

    assert index_data["files_indexed"] == 2
    assert index_data["total_tokens"] > 0
    assert index_data["indexed_extensions"] == [".md", ".py"]

    search_response = client.get(
        "/search",
        params={"query": "jwt token", "limit": 5},
    )

    assert search_response.status_code == 200

    search_data = search_response.json()

    assert search_data["query"] == "jwt token"
    assert search_data["result_count"] >= 1
    assert search_data["results"][0]["relative_path"] == "auth.py"
    assert search_data["results"][0]["matched_tokens"] == ["jwt", "token"]
    assert "snippets" in search_data["results"][0]
    assert len(search_data["results"][0]["snippets"]) >= 1
    assert "line_number" in search_data["results"][0]["snippets"][0]
    assert "text" in search_data["results"][0]["snippets"][0]


def test_index_repository_returns_404_for_missing_path(client: TestClient):
    response = client.post(
        "/index",
        json={"repo_path": "does-not-exist"},
    )

    assert response.status_code == 404


def test_search_respects_limit(client: TestClient, tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "auth.py").write_text("jwt auth", encoding="utf-8")
    (repo / "token.py").write_text("jwt token", encoding="utf-8")
    (repo / "service.py").write_text("jwt service", encoding="utf-8")

    client.post("/index", json={"repo_path": str(repo)})

    response = client.get(
        "/search",
        params={"query": "jwt", "limit": 2},
    )

    assert response.status_code == 200
    assert response.json()["result_count"] == 2

def test_search_returns_409_before_repository_is_indexed(client: TestClient):
    response = client.get(
        "/search",
        params={"query": "jwt"},
    )

    assert response.status_code == 409
    assert "No repository has been indexed yet" in response.json()["detail"]


def test_index_repository_returns_422_for_empty_repo(client: TestClient, tmp_path: Path):
    repo = tmp_path / "empty_repo"
    repo.mkdir()

    response = client.post(
        "/index",
        json={"repo_path": str(repo)},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "No supported source files were found to index."


def test_autocomplete_returns_identifier_suggestions(client: TestClient, tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "search.py").write_text(
        "class SearchEngine:\n"
        "    def search_repository(self):\n"
        "        searchable = True\n",
        encoding="utf-8",
    )

    index_response = client.post(
        "/index",
        json={"repo_path": str(repo)},
    )

    assert index_response.status_code == 200

    response = client.get(
        "/autocomplete",
        params={"prefix": "Search", "limit": 10},
    )

    assert response.status_code == 200
    assert response.json() == {
        "prefix": "Search",
        "suggestion_count": 4,
        "suggestions": [
            "search",
            "search_repository",
            "searchable",
            "SearchEngine",
        ],
    }


def test_autocomplete_returns_409_before_repository_is_indexed(client: TestClient):
    response = client.get(
        "/autocomplete",
        params={"prefix": "search"},
    )

    assert response.status_code == 409
    assert "No repository has been indexed yet" in response.json()["detail"]

def test_application_restart_hydrates_persisted_repository(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "restart_repository"
    repo.mkdir()

    (repo / "search.py").write_text(
        "restartpersistenttoken",
        encoding="utf-8",
    )

    with TestClient(app) as first_client:
        index_response = first_client.post(
            "/index",
            json={"repo_path": str(repo)},
        )

        assert index_response.status_code == 200

        initial_search_response = first_client.get(
            "/search",
            params={"query": "restartpersistenttoken"},
        )

        assert initial_search_response.status_code == 200

        initial_document_id = (
            initial_search_response.json()["results"][0]["document_id"]
        )

    # Simulate losing all process-local search state.
    search_engine.reset()

    assert search_engine.is_ready() is False

    # Starting a new application lifespan should rebuild the index
    # entirely from PostgreSQL.
    with TestClient(app) as restarted_client:
        restored_search_response = restarted_client.get(
            "/search",
            params={"query": "restartpersistenttoken"},
        )

        assert restored_search_response.status_code == 200

        restored_results = restored_search_response.json()["results"]

        assert len(restored_results) == 1
        assert (
            restored_results[0]["document_id"]
            == initial_document_id
        )
        assert restored_results[0]["relative_path"] == "search.py"