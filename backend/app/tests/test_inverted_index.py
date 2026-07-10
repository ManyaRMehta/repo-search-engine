from pathlib import Path

from app.models.source_file import SourceFile
from app.services.inverted_index import InvertedIndex


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