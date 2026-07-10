# Repository Crawler Design

## Problem

The search engine needs to read a local code repository and identify which files should be indexed for search.

In this project, each searchable source file is treated as a document.

## Requirements

The crawler should:

- Walk through a local repository directory.
- Ignore folders that should not be indexed, such as:
  - .git
  - node_modules
  - .venv
  - __pycache__
  - dist
  - build
  - target
- Skip binary files.
- Skip very large files.
- Include common source/code/documentation files.
- Return metadata for each valid file:
  - path
  - extension
  - file size
  - content

## Initial Supported File Types

- .py
- .js
- .ts
- .java
- .cs
- .go
- .md
- .txt
- .json
- .yml
- .yaml

## Design Decision

The crawler will not tokenize or rank files.

Its only responsibility is ingestion: finding readable files and returning clean file objects.

Tokenization, indexing, and ranking will be handled by separate services.

## Why This Separation Matters

Keeping crawling separate from tokenization and ranking makes the system easier to test, debug, and extend.

For example, if search results are bad, we can separately check:

1. Did the crawler find the right files?
2. Did the tokenizer split the content correctly?
3. Did the index store the terms correctly?
4. Did the ranker order the results correctly?