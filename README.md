# Repo Search Engine

A backend code search engine built with Python and FastAPI.

The system crawls local repositories, tokenizes source code, builds an inverted index, ranks results using BM25, generates line-level snippets, and provides prefix autocomplete. PostgreSQL persists indexed repositories across restarts, while Redis provides version-aware search caching with graceful fallback.

## Features

* Code-aware tokenization for `camelCase`, `PascalCase`, `snake_case`, and `kebab-case`
* Custom inverted index with term frequencies and matched line numbers
* BM25 relevance ranking
* Search-result snippets with source line numbers
* Trie-based prefix autocomplete
* Recursive repository crawling with file type, size, encoding, and ignored-directory filters
* PostgreSQL persistence for repositories, documents, and indexing history
* Document synchronization using SHA-256 content hashes
* Startup hydration of the active repository
* Redis cache-aside caching with versioned keys
* Direct BM25 fallback when Redis is unavailable
* FastAPI REST API
* Alembic migrations
* Docker Compose environment
* Pytest unit and integration tests
* GitHub Actions CI
* Search and Redis cache benchmarks

## Tech Stack

* Python 3.12
* FastAPI
* PostgreSQL 17
* SQLAlchemy
* Alembic
* Redis 8
* Pytest
* Docker
* GitHub Actions

## Architecture

```text
Local Repository
       |
       v
Repository Crawler
       |
       v
PostgreSQL Document Store
       |
       v
In-Memory Inverted Index
       |
       +-------------------+
       |                   |
       v                   v
  BM25 Ranker        Autocomplete Trie
       |
       v
  Search Service
       |
       +---- Redis Cache
       |
       v
    FastAPI
```

PostgreSQL is the durable source of indexed repository content. The inverted index, BM25 ranker, and autocomplete trie are rebuilt in memory from the active repository when the application starts.

## Indexing Flow

1. `POST /index` receives a local repository path.
2. The crawler finds supported UTF-8 files and ignores generated, dependency, and IDE directories.
3. PostgreSQL synchronizes newly created, updated, unchanged, and deleted files.
4. The application builds a new runtime search state from the persisted documents.
5. The repository's `index_version` is incremented.
6. The new inverted index, BM25 ranker, and autocomplete trie are activated together.

If re-indexing fails after a previous successful index exists, the last successful repository version remains available.

## Search and Caching

Search requests use a cache-aside flow:

1. A Redis key is generated from the repository ID, index version, normalized query tokens, and result limit.
2. Redis is checked for a cached response.
3. On a cache miss, the in-memory BM25 engine ranks matching documents.
4. Results are serialized to Redis with a configurable TTL.
5. Redis read or write failures fall back to direct BM25 retrieval without failing the request.

Including the repository's `index_version` in each key prevents stale results from being reused after re-indexing.

## API Endpoints

| Method | Endpoint        | Description                                        |
| ------ | --------------- | -------------------------------------------------- |
| `GET`  | `/health`       | Returns service status and indexed document count  |
| `POST` | `/index`        | Crawls, persists, and indexes a repository         |
| `GET`  | `/search`       | Returns ranked matches, line numbers, and snippets |
| `GET`  | `/autocomplete` | Returns prefix-based search suggestions            |

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

### Index a Repository

Local development:

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"repo_path":".."}'
```

Docker Compose:

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"repo_path":"/repositories/repo-search-engine"}'
```

### Search

```bash
curl "http://localhost:8000/search?query=repository%20crawler&limit=10"
```

### Autocomplete

```bash
curl "http://localhost:8000/autocomplete?prefix=repo&limit=10"
```

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

This starts:

* FastAPI on port `8000`
* PostgreSQL on host port `5433`
* Redis on host port `6379`

The API container:

* waits for PostgreSQL to become healthy
* runs Alembic migrations before startup
* runs as a non-root user
* exposes an HTTP health check
* mounts the repository read-only at `/repositories/repo-search-engine`

Stop the services:

```bash
docker compose down
```

Remove the PostgreSQL volume as well:

```bash
docker compose down -v
```

## Local Development

Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

Create the Python environment:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Apply migrations:

```bash
python -m alembic upgrade head
```

Start the API:

```bash
python -m uvicorn app.main:app --reload
```

## Environment Variables

| Variable                        | Default                                                                          |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `DATABASE_URL`                  | `postgresql+psycopg://repo_search:repo_search@localhost:5433/repo_search_engine` |
| `REDIS_URL`                     | `redis://localhost:6379/0`                                                       |
| `SEARCH_CACHE_TTL_SECONDS`      | `900`                                                                            |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | `0.5`                                                                            |
| `REDIS_SOCKET_TIMEOUT_SECONDS`  | `0.5`                                                                            |

## Tests

Run the full suite from `backend/` while PostgreSQL and Redis are running:

```bash
python -m pytest -q
```

Run unit tests only:

```bash
python -m pytest -q \
  -m "not postgres_integration and not redis_integration"
```

Run PostgreSQL integration tests:

```bash
python -m pytest -q -m postgres_integration
```

Run Redis integration tests:

```bash
python -m pytest -q -m redis_integration
```

| Test Category          |   Count |
| ---------------------- | ------: |
| Unit                   |      67 |
| PostgreSQL integration |      31 |
| Redis integration      |       3 |
| **Total**              | **101** |

## Continuous Integration

GitHub Actions runs four independent jobs:

1. Python dependency installation and 67 unit tests
2. PostgreSQL migrations and 31 integration tests
3. Redis service and 3 integration tests
4. Docker Compose validation and API image build

## Benchmarking

Run the search benchmark from `backend/`:

```bash
python -m scripts.benchmark_search --repo-path ..
```

Latest benchmark on this repository:

| Metric         |         Result |
| -------------- | -------------: |
| Files indexed  |             65 |
| Tokens indexed |         18,735 |
| Indexing time  |      41.285 ms |
| Query latency  | 0.080–0.414 ms |

The benchmark uses a clean archive of the committed public repository. Results depend on the repository snapshot, machine, and current system load.

### Redis Cache Benchmark

The Redis benchmark compared raw BM25 retrieval, cache misses, and cache hits over 100 iterations.

| Query              | Raw BM25 Median | Cache Miss Median | Cache Hit Median |
| ------------------ | --------------: | ----------------: | ---------------: |
| `search service`   |        0.161 ms |          0.754 ms |         0.224 ms |
| `runtime state`    |        0.051 ms |          0.394 ms |         0.175 ms |
| `redis cache`      |        0.081 ms |          0.410 ms |         0.163 ms |
| `bm25 ranker`      |        0.052 ms |          0.343 ms |         0.150 ms |
| `indexing service` |        0.104 ms |          0.375 ms |         0.152 ms |

Redis did not improve latency for this small, single-process workload because the in-memory BM25 search is faster than the Redis round trip and JSON deserialization. The cache remains useful as a shared optimization for more expensive searches or multiple API instances.

## Current Limitations

* One active repository at a time
* Lexical BM25 retrieval only
* Full in-memory index rebuild after successful indexing
* No automatic repository synchronization
* Fixed set of supported source-file extensions
* No authentication or authorization
* Redis adds overhead for the current small benchmark workload

## Possible Improvements

* Incremental runtime index updates
* Repository synchronization jobs
* Search pagination and file filters
* Metrics and observability
* Concurrent indexing protection
* Larger-corpus performance testing
* Hybrid lexical and semantic retrieval
