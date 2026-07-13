from app.services.autocomplete_index import AutocompleteIndex


def test_insert_and_suggest_single_term():
    autocomplete = AutocompleteIndex()

    autocomplete.insert("token")

    assert autocomplete.suggest("tok") == ["token"]


def test_insert_multiple_terms_with_shared_prefix():
    autocomplete = AutocompleteIndex()

    autocomplete.insert("token")
    autocomplete.insert("tokenizer")
    autocomplete.insert("tokenization")

    assert autocomplete.suggest("tok") == [
        "token",
        "tokenization",
        "tokenizer",
    ]


def test_unknown_prefix_returns_empty_list():
    autocomplete = AutocompleteIndex()

    autocomplete.insert("token")

    assert autocomplete.suggest("xyz") == []


def test_build_multiple_terms():
    autocomplete = AutocompleteIndex()

    autocomplete.build(
        {
            "repository",
            "repo",
            "search",
        }
    )

    assert autocomplete.suggest("rep") == [
        "repo",
        "repository",
    ]