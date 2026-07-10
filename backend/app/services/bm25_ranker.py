import math
from collections import defaultdict

from app.models.search_result import SearchResult
from app.services.code_tokenizer import CodeTokenizer
from app.services.inverted_index import InvertedIndex
from app.models.search_result import SearchResult, SnippetLine

MAX_SNIPPET_LINES = 5
MAX_SNIPPET_LINE_LENGTH = 160

class BM25Ranker:
    """
    Ranks documents from an inverted index using the BM25 scoring algorithm.
    """

    def __init__(
        self,
        index: InvertedIndex,
        tokenizer: CodeTokenizer | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.index = index
        self.tokenizer = tokenizer or CodeTokenizer()
        self.k1 = k1
        self.b = b

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        query_tokens = self.tokenizer.tokenize(query)

        if not query_tokens:
            return []

        scores: dict[int, float] = defaultdict(float)
        matched_tokens_by_document: dict[int, set[str]] = defaultdict(set)
        line_numbers_by_document: dict[int, set[int]] = defaultdict(set)

        average_document_length = self._average_document_length()

        if average_document_length == 0:
            return []

        for token in query_tokens:
            document_frequency = self.index.document_frequency(token)

            if document_frequency == 0:
                continue

            inverse_document_frequency = self._inverse_document_frequency(
                document_frequency
            )

            for posting in self.index.get_postings(token):
                document = self.index.get_document(posting.document_id)

                if document is None:
                    continue

                score = self._score_term(
                    term_frequency=posting.term_frequency,
                    document_length=document.total_tokens,
                    average_document_length=average_document_length,
                    inverse_document_frequency=inverse_document_frequency,
                )

                scores[document.document_id] += score
                matched_tokens_by_document[document.document_id].add(token)
                line_numbers_by_document[document.document_id].update(
                    posting.line_numbers
                )

        results = []

        for document_id, score in scores.items():
            document = self.index.get_document(document_id)

            if document is None:
                continue

            results.append(
                SearchResult(
                    document_id=document_id,
                    relative_path=document.relative_path,
                    score=score,
                    matched_tokens=sorted(matched_tokens_by_document[document_id]),
                    line_numbers=sorted(line_numbers_by_document[document_id]),
                    snippets=self._build_snippets(
                    document_lines=document.lines,
                    line_numbers=line_numbers_by_document[document_id],
                    ),
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    def _average_document_length(self) -> float:
        if not self.index.documents:
            return 0

        total_tokens = sum(
            document.total_tokens for document in self.index.documents.values()
        )

        return total_tokens / len(self.index.documents)

    def _inverse_document_frequency(self, document_frequency: int) -> float:
        total_documents = self.index.total_documents()

        return math.log(
            1 + (total_documents - document_frequency + 0.5)
            / (document_frequency + 0.5)
        )

    def _score_term(
        self,
        term_frequency: int,
        document_length: int,
        average_document_length: float,
        inverse_document_frequency: float,
    ) -> float:
        numerator = term_frequency * (self.k1 + 1)

        denominator = term_frequency + self.k1 * (
            1 - self.b + self.b * (document_length / average_document_length)
        )

        return inverse_document_frequency * (numerator / denominator)
    
    def _build_snippets(
        self,
        document_lines: list[str],
        line_numbers: set[int],
    ) -> list[SnippetLine]:
        snippets: list[SnippetLine] = []

        for line_number in sorted(line_numbers):
            if len(snippets) >= MAX_SNIPPET_LINES:
                break

            line_index = line_number - 1

            if line_index < 0 or line_index >= len(document_lines):
                continue

            snippets.append(
                SnippetLine(
                    line_number=line_number,
                    text=self._truncate_snippet_line(document_lines[line_index]),
                )
            )

        return snippets

    def _truncate_snippet_line(self, line: str) -> str:
        cleaned_line = line.rstrip()

        if len(cleaned_line) <= MAX_SNIPPET_LINE_LENGTH:
            return cleaned_line

        return cleaned_line[: MAX_SNIPPET_LINE_LENGTH - 3] + "..."