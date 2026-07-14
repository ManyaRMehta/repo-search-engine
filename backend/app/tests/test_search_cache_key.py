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

def test_search_cache_key_changes_with_index_version() -> None:
    builder = SearchCacheKeyBuilder()

    version_three_key = builder.build(
        repository_id=7,
        index_version=3,
        query="jwt token",
        limit=5,
    )

    version_four_key = builder.build(
        repository_id=7,
        index_version=4,
        query="jwt token",
        limit=5,
    )

    assert version_three_key != version_four_key
    assert ":version-3:" in version_three_key
    assert ":version-4:" in version_four_key