# Repo Search Engine

A backend search engine for source code repositories built from first principles. The project indexes local repositories, builds an in-memory inverted index, ranks results using BM25, and exposes search functionality through a FastAPI REST API.

The goal of this project is to explore the core concepts behind modern code search systems while emphasizing clean architecture, testing, and backend engineering fundamentals.

---

## Features

- Repository crawler for local codebases
- Code-aware tokenizer
- In-memory inverted index
- BM25 ranking algorithm
- FastAPI search API
- Search result snippets
- Benchmark runner for indexing and query latency
- Comprehensive unit test suite

---

## Tech Stack

- Python
- FastAPI
- BM25 Information Retrieval
- Pytest

---

## Architecture

```
Repository
    │
    ▼
Repository Crawler
    │
    ▼
Code Tokenizer
    │
    ▼
Inverted Index
    │
    ▼
BM25 Ranker
    │
    ▼
Search Engine
    │
    ▼
FastAPI API
```

---

## Benchmark

Current benchmark on this repository:

| Metric | Value |
|---------|------:|
| Files Indexed | 39 |
| Tokens Indexed | 5,743 |
| Indexing Time | 22.9 ms |
| Search Latency | 0.04–0.33 ms |

---

## Running Locally

```bash
git clone <repository-url>
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -e .
uvicorn app.main:app --reload
```

---

## Running Tests

```bash
pytest
```

---

## Benchmarking

```bash
python3 -m scripts.benchmark_search --repo-path ..
```

---

## Roadmap

### Completed

- [x] Repository crawling
- [x] Code-aware tokenization
- [x] Inverted index
- [x] BM25 ranking
- [x] Search orchestration
- [x] FastAPI endpoints
- [x] Search snippets
- [x] Benchmark runner
- [x] Unit tests

### Planned

- [ ] Prefix autocomplete
- [ ] PostgreSQL persistence
- [ ] Redis query caching
- [ ] Hybrid semantic search (BM25 + embeddings)
- [ ] Docker support
- [ ] GitHub Actions CI

---

## Project Status

This project is actively being developed with a focus on backend search systems, information retrieval, and production-oriented software engineering practices.