from pathlib import Path

from app.models.indexing_summary import IndexingSummary
from app.models.search_result import SearchResult
from app.services.bm25_ranker import BM25Ranker
from app.services.inverted_index import InvertedIndex
from app.services.repository_crawler import RepositoryCrawler


class SearchEngine:
    """
    Coordinates the full in-memory search pipeline.

    Pipeline:
    repository path -> crawler -> inverted index -> BM25 ranker -> search results
    """

    def __init__(self, crawler: RepositoryCrawler | None = None):
        self.crawler = crawler or RepositoryCrawler()
        self.index = InvertedIndex()
        self.ranker = BM25Ranker(self.index)
        self.indexed_repo_path: Path | None = None

    def index_repository(self, repo_path: str | Path) -> IndexingSummary:
        resolved_repo_path = Path(repo_path).resolve()

        source_files = self.crawler.crawl(resolved_repo_path)

        # Rebuild the index from scratch each time.
        # Later, we can improve this with incremental indexing.
        self.index = InvertedIndex()
        document_ids = self.index.add_documents(source_files)
        self.ranker = BM25Ranker(self.index)
        self.indexed_repo_path = resolved_repo_path

        total_tokens = sum(
            document.total_tokens for document in self.index.documents.values()
        )

        indexed_extensions = sorted(
            {
                document.extension
                for document in self.index.documents.values()
            }
        )

        return IndexingSummary(
            repo_path=str(resolved_repo_path),
            files_indexed=len(document_ids),
            total_tokens=total_tokens,
            indexed_extensions=indexed_extensions,
        )

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self.ranker.search(query=query, limit=limit)

    def total_documents(self) -> int:
        return self.index.total_documents()