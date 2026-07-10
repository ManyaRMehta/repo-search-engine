# Search Engine Service Design

## Problem

The crawler, tokenizer, inverted index, and BM25 ranker currently work as separate components.

The backend needs one higher-level service that coordinates the full search workflow:

repo path -> crawl files -> build index -> run ranked search

## Responsibilities

The SearchEngine service should:

- Accept a repository path.
- Use RepositoryCrawler to find source files.
- Build a fresh in-memory inverted index.
- Use BM25Ranker to search the indexed repository.
- Return a summary after indexing.
- Return ranked search results for queries.

## Design Decision

The SearchEngine service will orchestrate the pipeline but will not contain crawling, tokenization, indexing, or ranking logic directly.

This keeps responsibilities separated:

- RepositoryCrawler handles file discovery.
- CodeTokenizer handles tokenization.
- InvertedIndex handles term-to-document mappings.
- BM25Ranker handles ranking.
- SearchEngine coordinates the workflow.

## Why This Matters

This makes the project easier to test and easier to explain.

If search results are wrong, we can debug each layer separately:

1. Did the crawler find the right files?
2. Did the tokenizer produce the right tokens?
3. Did the index store the terms correctly?
4. Did BM25 rank the documents correctly?
5. Did the SearchEngine connect the steps correctly?