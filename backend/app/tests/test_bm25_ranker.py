from pathlib import Path

from app.models.source_file import SourceFile
from app.services.bm25_ranker import BM25Ranker
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


def test_ranker_returns_matching_document():
    index = InvertedIndex()
    index.add_document(make_source_file("auth.py", "jwt token validation"))

    ranker = BM25Ranker(index)
    results = ranker.search("jwt")

    assert len(results) == 1
    assert results[0].relative_path == "auth.py"
    assert results[0].matched_tokens == ["jwt"]


def test_ranker_orders_more_relevant_document_first():
    index = InvertedIndex()
    index.add_documents(
        [
            make_source_file("auth.py", "jwt jwt jwt token validation"),
            make_source_file("readme.md", "jwt overview"),
        ]
    )

    ranker = BM25Ranker(index)
    results = ranker.search("jwt")

    assert len(results) == 2
    assert results[0].relative_path == "auth.py"


def test_ranker_returns_empty_list_for_no_matches():
    index = InvertedIndex()
    index.add_document(make_source_file("auth.py", "jwt token validation"))

    ranker = BM25Ranker(index)
    results = ranker.search("database")

    assert results == []


def test_ranker_tracks_matching_line_numbers():
    index = InvertedIndex()
    index.add_document(
        make_source_file(
            "auth.py",
            "jwt token\n"
            "validate user\n"
            "refresh jwt\n",
        )
    )

    ranker = BM25Ranker(index)
    results = ranker.search("jwt")

    assert results[0].line_numbers == [1, 3]


def test_ranker_handles_multi_term_query():
    index = InvertedIndex()
    index.add_documents(
        [
            make_source_file("auth.py", "jwt token validation"),
            make_source_file("user.py", "user profile service"),
        ]
    )

    ranker = BM25Ranker(index)
    results = ranker.search("jwt token")

    assert len(results) == 1
    assert results[0].relative_path == "auth.py"
    assert results[0].matched_tokens == ["jwt", "token"]


def test_ranker_respects_limit():
    index = InvertedIndex()
    index.add_documents(
        [
            make_source_file("auth.py", "jwt"),
            make_source_file("token.py", "jwt"),
            make_source_file("service.py", "jwt"),
        ]
    )

    ranker = BM25Ranker(index)
    results = ranker.search("jwt", limit=2)

    assert len(results) == 2