from pathlib import Path

from app.models.source_file import SourceFile
from app.services.inverted_index import InvertedIndex
import pytest


def make_source_file(relative_path: str, content: str) -> SourceFile:
    path = Path("/fake/repo") / relative_path

    return SourceFile(
        path=path,
        relative_path=relative_path,
        extension=path.suffix,
        size_bytes=len(content.encode("utf-8")),
        content=content,
    )


def test_index_adds_document_metadata():
    source_file = make_source_file("auth.py", "jwt token")

    index = InvertedIndex()
    document_id = index.add_document(source_file)

    document = index.get_document(document_id)

    assert document is not None
    assert document.relative_path == "auth.py"
    assert document.total_tokens == 2
    assert index.total_documents() == 1


def test_index_maps_token_to_document():
    source_file = make_source_file("auth.py", "jwt token")

    index = InvertedIndex()
    document_id = index.add_document(source_file)

    postings = index.get_postings("jwt")

    assert len(postings) == 1
    assert postings[0].document_id == document_id


def test_index_tracks_term_frequency():
    source_file = make_source_file("auth.py", "jwt jwt token")

    index = InvertedIndex()
    index.add_document(source_file)

    postings = index.get_postings("jwt")

    assert len(postings) == 1
    assert postings[0].term_frequency == 2


def test_index_tracks_line_numbers():
    source_file = make_source_file(
        "auth.py",
        "jwt token\n"
        "validate jwt\n",
    )

    index = InvertedIndex()
    index.add_document(source_file)

    postings = index.get_postings("jwt")

    assert len(postings) == 1
    assert postings[0].line_numbers == {1, 2}


def test_index_document_frequency_counts_documents_not_occurrences():
    first_file = make_source_file("auth.py", "jwt jwt token")
    second_file = make_source_file("service.py", "jwt service")

    index = InvertedIndex()
    index.add_documents([first_file, second_file])

    assert index.document_frequency("jwt") == 2


def test_index_returns_empty_list_for_missing_token():
    source_file = make_source_file("auth.py", "jwt token")

    index = InvertedIndex()
    index.add_document(source_file)

    assert index.get_postings("missing") == []


def test_index_handles_multiple_documents():
    first_file = make_source_file("auth.py", "jwt token")
    second_file = make_source_file("user.py", "user profile")

    index = InvertedIndex()
    document_ids = index.add_documents([first_file, second_file])

    assert document_ids == [1, 2]
    assert index.total_documents() == 2

    jwt_postings = index.get_postings("jwt")
    user_postings = index.get_postings("user")

    assert jwt_postings[0].document_id == 1
    assert user_postings[0].document_id == 2

def test_add_document_accepts_explicit_document_id(
    tmp_path: Path,
) -> None:
    index = InvertedIndex()

    first_file = SourceFile(
        path=tmp_path / "first.py",
        relative_path="first.py",
        extension=".py",
        size_bytes=5,
        content="first",
    )

    second_file = SourceFile(
        path=tmp_path / "second.py",
        relative_path="second.py",
        extension=".py",
        size_bytes=6,
        content="second",
    )

    explicit_id = index.add_document(
        first_file,
        document_id=42,
    )
    automatic_id = index.add_document(second_file)

    assert explicit_id == 42
    assert automatic_id == 43
    assert index.get_document(42) is not None
    assert index.get_document(43) is not None

def test_add_document_rejects_duplicate_document_id(
    tmp_path: Path,
) -> None:
    index = InvertedIndex()

    source_file = SourceFile(
        path=tmp_path / "main.py",
        relative_path="main.py",
        extension=".py",
        size_bytes=4,
        content="main",
    )

    index.add_document(source_file, document_id=10)

    with pytest.raises(
        ValueError,
        match="Document ID already exists",
    ):
        index.add_document(source_file, document_id=10)