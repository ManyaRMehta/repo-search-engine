import hashlib
import json

from app.services.code_tokenizer import CodeTokenizer


CACHE_NAMESPACE = "repo-search"
CACHE_SCHEMA_VERSION = "v1"


class SearchCacheKeyBuilder:
    """Builds deterministic keys for cached search results."""

    def __init__(
        self,
        tokenizer: CodeTokenizer | None = None,
    ) -> None:
        self.tokenizer = tokenizer or CodeTokenizer()

    def build(
        self,
        *,
        repository_id: int,
        index_version: int,
        query: str,
        limit: int,
    ) -> str:
        normalized_tokens = sorted(
            self.tokenizer.tokenize(query)
        )

        payload = {
            "tokens": normalized_tokens,
            "limit": limit,
        }

        canonical_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        request_hash = hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()

        return (
            f"{CACHE_NAMESPACE}:"
            f"{CACHE_SCHEMA_VERSION}:"
            f"search:"
            f"repository-{repository_id}:"
            f"version-{index_version}:"
            f"{request_hash}"
        )
    