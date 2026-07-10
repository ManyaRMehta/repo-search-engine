from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    """
    Represents one ranked search result.

    The API layer will eventually return these results to users.
    """

    document_id: int
    relative_path: str
    score: float
    matched_tokens: list[str]
    line_numbers: list[int]