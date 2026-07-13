from pathlib import Path
import pytest
from app.api.routes import search_engine
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
@pytest.fixture(autouse=True)
def reset_search_engine_between_tests():
    search_engine.reset()


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "indexed_documents" in response.json()


def test_index_repository_and_search(tmp_path: Path):
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


def test_index_repository_returns_404_for_missing_path():
    response = client.post(
        "/index",
        json={"repo_path": "does-not-exist"},
    )

    assert response.status_code == 404


def test_search_respects_limit(tmp_path: Path):
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

def test_search_returns_409_before_repository_is_indexed():
    response = client.get(
        "/search",
        params={"query": "jwt"},
    )

    assert response.status_code == 409
    assert "No repository has been indexed yet" in response.json()["detail"]


def test_index_repository_returns_422_for_empty_repo(tmp_path: Path):
    repo = tmp_path / "empty_repo"
    repo.mkdir()

    response = client.post(
        "/index",
        json={"repo_path": str(repo)},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "No supported source files were found to index."