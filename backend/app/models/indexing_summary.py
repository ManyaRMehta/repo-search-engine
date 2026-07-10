from dataclasses import dataclass


@dataclass(frozen=True)
class IndexingSummary:
    """
    Summary returned after indexing a repository.

    This is useful for APIs, logs, debugging, and later benchmarks.
    """

    repo_path: str
    files_indexed: int
    total_tokens: int
    indexed_extensions: list[str]