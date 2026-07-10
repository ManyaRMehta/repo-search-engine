from dataclasses import dataclass


@dataclass(frozen=True)
class TokenizedLine:
    """
    Represents the searchable tokens found on a specific line of a file.

    This will help the indexer connect search terms back to line numbers,
    which later allows the API to return useful code snippets.
    """

    line_number: int
    tokens: list[str]