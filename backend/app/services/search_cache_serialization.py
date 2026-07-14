import json

from app.models.search_result import SearchResult, SnippetLine


class SearchCacheSerializationError(ValueError):
    """Raised when cached search results cannot be decoded safely."""

def serialize_search_results(
    results: list[SearchResult],
) -> str:
    payload = [
        {
            "document_id": result.document_id,
            "relative_path": result.relative_path,
            "score": result.score,
            "matched_tokens": result.matched_tokens,
            "line_numbers": result.line_numbers,
            "snippets": [
                {
                    "line_number": snippet.line_number,
                    "text": snippet.text,
                }
                for snippet in result.snippets
            ],
        }
        for result in results
    ]

    return json.dumps(
        payload,
        separators=(",", ":"),
    )


def deserialize_search_results(
    payload: str,
) -> list[SearchResult]:
    try:
        raw_results = json.loads(payload)

        return [
            SearchResult(
                document_id=result["document_id"],
                relative_path=result["relative_path"],
                score=result["score"],
                matched_tokens=result["matched_tokens"],
                line_numbers=result["line_numbers"],
                snippets=[
                    SnippetLine(
                        line_number=snippet["line_number"],
                        text=snippet["text"],
                    )
                    for snippet in result["snippets"]
                ],
            )
            for result in raw_results
        ]
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
    ) as error:
        raise SearchCacheSerializationError(
            "Invalid cached search-result JSON"
        ) from error

