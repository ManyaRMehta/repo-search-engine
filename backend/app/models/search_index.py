from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndexedDocument:
    """
    Represents a source file after it has been added to the search index.
    """

    document_id: int
    path: Path
    relative_path: str
    extension: str
    size_bytes: int
    total_tokens: int
    lines : list[str] 


@dataclass
class Posting:
    """
    Represents one token's occurrence information inside one document.

    Example:
    token "jwt" appears in auth.py 4 times on lines 3, 10, and 18.
    """

    document_id: int
    term_frequency: int
    line_numbers: set[int]