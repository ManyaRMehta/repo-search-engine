from app.services.code_tokenizer import CodeTokenizer


def test_tokenizer_lowercases_words():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("Hello WORLD")

    assert tokens == ["hello", "world"]


def test_tokenizer_splits_snake_case():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("jwt_token_service")

    assert tokens == ["jwt", "token", "service"]


def test_tokenizer_splits_kebab_case():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("repo-search-engine")

    assert tokens == ["repo", "search", "engine"]


def test_tokenizer_splits_camel_case():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("getUserById")

    assert tokens == ["get", "user", "by", "id"]


def test_tokenizer_splits_pascal_case():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("RepositoryCrawler")

    assert tokens == ["repository", "crawler"]


def test_tokenizer_preserves_duplicate_tokens():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("jwt jwt token")

    assert tokens == ["jwt", "jwt", "token"]


def test_tokenizer_filters_single_character_tokens():
    tokenizer = CodeTokenizer()

    tokens = tokenizer.tokenize("i x db api")

    assert tokens == ["db", "api"]


def test_tokenizer_tracks_line_numbers():
    tokenizer = CodeTokenizer()

    tokenized_lines = tokenizer.tokenize_by_line(
        "def getUserById():\n"
        "    return jwt_token\n"
    )

    assert len(tokenized_lines) == 2

    assert tokenized_lines[0].line_number == 1
    assert tokenized_lines[0].tokens == ["def", "get", "user", "by", "id"]

    assert tokenized_lines[1].line_number == 2
    assert tokenized_lines[1].tokens == ["return", "jwt", "token"]

def test_extract_identifiers_preserves_full_code_identifiers():
    tokenizer = CodeTokenizer()

    identifiers = tokenizer.extract_identifiers(
        "class SearchEngine:\n"
        "    def index_repository(self, repo_path2):\n"
        "        _private_value = repo_path2\n"
    )

    assert "SearchEngine" in identifiers
    assert "index_repository" in identifiers
    assert "repo_path2" in identifiers
    assert "_private_value" in identifiers