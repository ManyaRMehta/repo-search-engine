from app.models.search_result import SearchResult, SnippetLine
from app.services.search_cache_serialization import (
    deserialize_search_results,
    serialize_search_results,
    SearchCacheSerializationError,
)
import pytest




def test_search_results_survive_json_round_trip() -> None:
    original_results = [
        SearchResult(
            document_id=42,
            relative_path="app/auth.py",
            score=3.75,
            matched_tokens=["jwt", "token"],
            line_numbers=[10, 14],
            snippets=[
                SnippetLine(
                    line_number=10,
                    text="def validate_jwt_token(token):",
                ),
                SnippetLine(
                    line_number=14,
                    text="return token_is_valid",
                ),
            ],
        )
    ]

    payload = serialize_search_results(original_results)
    restored_results = deserialize_search_results(payload)

    assert isinstance(payload, str)
    assert restored_results == original_results

def test_empty_search_results_survive_json_round_trip() -> None:
    payload = serialize_search_results([])
    restored_results = deserialize_search_results(payload)

    assert payload == "[]"
    assert restored_results == []


def test_deserialize_rejects_malformed_json() -> None:
    with pytest.raises(
        SearchCacheSerializationError,
        match="Invalid cached search-result JSON",
    ):
        deserialize_search_results("not valid json")