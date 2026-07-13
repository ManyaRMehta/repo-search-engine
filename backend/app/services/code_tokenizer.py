import re


from app.models.tokenized_line import TokenizedLine


MIN_TOKEN_LENGTH = 2
IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


class CodeTokenizer:
    """
    Converts source code text into searchable tokens.

    This tokenizer is designed for code search, so it handles common
    programming identifier styles like camelCase, PascalCase, snake_case,
    and kebab-case.
    """

    def tokenize(self, text: str) -> list[str]:
        normalized_text = self._split_identifier_boundaries(text)
        raw_parts = re.split(r"[^A-Za-z0-9]+", normalized_text)

        return [
            part.lower()
            for part in raw_parts
            if len(part) >= MIN_TOKEN_LENGTH
        ]
    
    def extract_identifiers(self, text: str) -> list[str]:
        return IDENTIFIER_PATTERN.findall(text)

    def tokenize_by_line(self, text: str) -> list[TokenizedLine]:
        tokenized_lines: list[TokenizedLine] = []

        for line_number, line in enumerate(text.splitlines(), start=1):
            tokens = self.tokenize(line)

            if tokens:
                tokenized_lines.append(
                    TokenizedLine(
                        line_number=line_number,
                        tokens=tokens,
                    )
                )

        return tokenized_lines

    def _split_identifier_boundaries(self, text: str) -> str:
        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)

        return text