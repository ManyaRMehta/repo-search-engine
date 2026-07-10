from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    """
    Represents one file that can be indexed by the search engine.

    The crawler is responsible for creating SourceFile objects.
    Later components, like the tokenizer and indexer, will consume them.
    """

    path: Path
    relative_path: str
    extension: str
    size_bytes: int
    content: str