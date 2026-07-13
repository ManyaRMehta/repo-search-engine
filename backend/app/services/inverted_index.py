from collections import defaultdict

from app.models.search_index import IndexedDocument, Posting
from app.models.source_file import SourceFile
from app.services.code_tokenizer import CodeTokenizer


class InvertedIndex:
    """
    In-memory inverted index for code search.

    Maps each token to the documents where that token appears.
    """

    def __init__(self, tokenizer: CodeTokenizer | None = None):
        self.tokenizer = tokenizer or CodeTokenizer()
        self.documents: dict[int, IndexedDocument] = {}
        self.postings: dict[str, dict[int, Posting]] = defaultdict(dict)
        self.identifiers: set[str] = set()
        self._next_document_id = 1

    def add_document(self, source_file: SourceFile) -> int:
        document_id = self._next_document_id
        self._next_document_id += 1

        tokenized_lines = self.tokenizer.tokenize_by_line(source_file.content)
        self.identifiers.update(
            self.tokenizer.extract_identifiers(source_file.content)
        )
        all_tokens = [
            token
            for tokenized_line in tokenized_lines
            for token in tokenized_line.tokens
        ]

        indexed_document = IndexedDocument(
            document_id=document_id,
            path=source_file.path,
            relative_path=source_file.relative_path,
            extension=source_file.extension,
            size_bytes=source_file.size_bytes,
            total_tokens=len(all_tokens),
            lines = source_file.content.splitlines(),
        )

        self.documents[document_id] = indexed_document

        for tokenized_line in tokenized_lines:
            for token in tokenized_line.tokens:
                document_postings = self.postings[token]

                if document_id not in document_postings:
                    document_postings[document_id] = Posting(
                        document_id=document_id,
                        term_frequency=0,
                        line_numbers=set(),
                    )

                posting = document_postings[document_id]
                posting.term_frequency += 1
                posting.line_numbers.add(tokenized_line.line_number)

        return document_id

    def add_documents(self, source_files: list[SourceFile]) -> list[int]:
        return [self.add_document(source_file) for source_file in source_files]

    def get_postings(self, token: str) -> list[Posting]:
        normalized_token = token.lower()
        return list(self.postings.get(normalized_token, {}).values())

    def get_document(self, document_id: int) -> IndexedDocument | None:
        return self.documents.get(document_id)

    def document_frequency(self, token: str) -> int:
        normalized_token = token.lower()
        return len(self.postings.get(normalized_token, {}))

    def total_documents(self) -> int:
        return len(self.documents)
    
    def vocabulary(self) -> set[str]:
        return set(self.postings.keys())
    
    def identifier_vocabulary(self) -> set[str]:
        return set(self.identifiers)