from dataclasses import dataclass


@dataclass(frozen=True)
class SnippetLine:
    """
    Represents one line of source code shown in a search result preview.
    """

    line_number: int
    text: str


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
    snippets: list[SnippetLine]