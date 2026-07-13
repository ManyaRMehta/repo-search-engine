from operator import index
from pathlib import Path

from app.models.indexing_summary import IndexingSummary
from app.models.search_result import SearchResult
from app.services.bm25_ranker import BM25Ranker
from app.services.inverted_index import InvertedIndex
from app.services.repository_crawler import RepositoryCrawler
from app.services.autocomplete_index import AutocompleteIndex
from app.models.source_file import SourceFile
from app.services.runtime_search_state import RuntimeSearchState


class SearchEngine:
    """
    Coordinates the full in-memory search pipeline.

    Pipeline:
    repository path -> crawler -> inverted index -> BM25 ranker -> search results
    """

    def __init__(self, crawler: RepositoryCrawler | None = None):
        self.crawler = crawler or RepositoryCrawler()
        self.index = InvertedIndex()
        self.autocomplete = AutocompleteIndex()
        self.ranker = BM25Ranker(self.index)
        self.indexed_repo_path: Path | None = None

    def index_repository(self, repo_path: str | Path) -> IndexingSummary:
        resolved_repo_path = Path(repo_path).resolve()

        source_files = self.crawler.crawl(resolved_repo_path)

        new_index = InvertedIndex()
        document_ids = new_index.add_documents(source_files)

        self._replace_runtime_index(
            index=new_index,
            repo_path=resolved_repo_path,
        )

        total_tokens = sum(
            document.total_tokens for document in new_index.documents.values()
        )

        indexed_extensions = sorted(
            {
                document.extension
                for document in new_index.documents.values()
            }
        )

        return IndexingSummary(
            repo_path=str(resolved_repo_path),
            files_indexed=len(document_ids),
            total_tokens=total_tokens,
            indexed_extensions=indexed_extensions,
        )
    
    def load_documents(
        self,
        repo_path: str | Path,
        documents: list[tuple[int, SourceFile]],
    ) -> None:
        state = self.build_runtime_state(
            repo_path=repo_path,
            documents=documents,
        )

        self.activate_runtime_state(state)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self.ranker.search(query=query, limit=limit)
    
    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        return self.autocomplete.suggest(prefix=prefix, limit=limit)

    def total_documents(self) -> int:
        return self.index.total_documents()
    
    def is_ready(self) -> bool:
        return self.total_documents() > 0

    def reset(self) -> None:
        self.index = InvertedIndex()
        self.autocomplete = AutocompleteIndex()
        self.ranker = BM25Ranker(self.index)
        self.indexed_repo_path = None

    def _replace_runtime_index(
        self,
        *,
        index: InvertedIndex,
        repo_path: Path,
    ) -> None:
        autocomplete = AutocompleteIndex()

        autocomplete_terms = (
            index.vocabulary()
            | index.identifier_vocabulary()
        )

        autocomplete.build(autocomplete_terms)

        state = RuntimeSearchState(
            index=index,
            autocomplete=autocomplete,
            ranker=BM25Ranker(index),
            repo_path=repo_path,
        )

        self.activate_runtime_state(state)

    def build_runtime_state(
        self,
        repo_path: str | Path,
        documents: list[tuple[int, SourceFile]],
    ) -> RuntimeSearchState:
        resolved_repo_path = Path(repo_path).resolve()
        index = InvertedIndex()

        for document_id, source_file in documents:
            index.add_document(
                source_file,
                document_id=document_id,
            )

        autocomplete = AutocompleteIndex()

        autocomplete_terms = (
            index.vocabulary()
            | index.identifier_vocabulary()
        )

        autocomplete.build(autocomplete_terms)
    
        return RuntimeSearchState(
            index=index,
            autocomplete=autocomplete,
            ranker=BM25Ranker(index),
            repo_path=resolved_repo_path,
       )

    def activate_runtime_state(
        self,
        state: RuntimeSearchState,
    ) -> None:
        self.index = state.index
        self.autocomplete = state.autocomplete
        self.ranker = state.ranker
        self.indexed_repo_path = state.repo_path