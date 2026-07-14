from dataclasses import dataclass
from pathlib import Path

from app.services.autocomplete_index import AutocompleteIndex
from app.services.bm25_ranker import BM25Ranker
from app.services.inverted_index import InvertedIndex


@dataclass(frozen=True)
class RuntimeSearchState:
    index: InvertedIndex
    autocomplete: AutocompleteIndex
    ranker: BM25Ranker
    repo_path: Path