# Benchmarking Design

## Problem

The search engine needs measurable performance data for documentation, resume bullets, and technical interviews.

Instead of saying the system is fast, we should measure:

- indexing time
- number of indexed files
- number of indexed tokens
- query latency
- number of returned results

## Requirements

The benchmark runner should:

- accept a local repository path
- index the repository using the existing SearchEngine service
- run a fixed set of representative search queries
- measure indexing time in milliseconds
- measure query latency in milliseconds
- print a readable report

## Design Decision

The benchmark runner will use the existing SearchEngine service instead of duplicating crawler, indexing, or ranking logic.

This keeps benchmarking separate from the search implementation.

## Why This Matters

Benchmarks make the project stronger because they show performance awareness.

They also create concrete numbers that can be used in the README and resume.

## Redis Cache Benchmark

The Redis benchmark compares three search paths:

1. Raw in-memory BM25 retrieval
2. Redis cache miss, including Redis GET, BM25 retrieval, JSON serialization, and Redis SET
3. Redis cache hit, including Redis GET and JSON deserialization

Each path was measured over 100 iterations. The benchmark reports median and nearest-rank p95 latency.

The benchmark used the repo-search-engine repository itself:

- Files indexed: 78
- Tokens indexed: 18,984
- Result limit: 10

### Results

| Query | Raw BM25 Median | Cache Miss Median | Cache Hit Median |
|---|---:|---:|---:|
| search service | 0.161 ms | 0.754 ms | 0.224 ms |
| runtime state | 0.051 ms | 0.394 ms | 0.175 ms |
| redis cache | 0.081 ms | 0.410 ms | 0.163 ms |
| bm25 ranker | 0.052 ms | 0.343 ms | 0.150 ms |
| indexing service | 0.104 ms | 0.375 ms | 0.152 ms |

### Interpretation

Redis did not improve query latency for the current single-process workload. The in-memory BM25 engine searches this relatively small index faster than the Redis network round trip and JSON deserialization required for a cache hit.

The cache remains useful as a shared optimization for multi-instance deployments and for future workloads where retrieval, ranking, filtering, or response construction becomes more expensive. Redis remains optional: cache failures fall back to direct BM25 retrieval without failing the search request.