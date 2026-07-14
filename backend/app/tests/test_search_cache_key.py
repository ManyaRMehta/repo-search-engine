from app.services.search_cache_key import SearchCacheKeyBuilder


def test_search_cache_key_normalizes_equivalent_queries() -> None:
    builder = SearchCacheKeyBuilder()

    camel_case_key = builder.build(
        repository_id=7,
        index_version=3,
        query="JWTToken",
        limit=5,
    )

    reordered_key = builder.build(
        repository_id=7,
        index_version=3,
        query="token jwt",
        limit=5,
    )

    assert camel_case_key == reordered_key
    assert camel_case_key.startswith(
        "repo-search:v1:search:repository-7:version-3:"
    )