# Code Tokenizer Design

## Problem

The search engine needs to convert source code into searchable terms.

A normal text tokenizer is not enough because code often uses naming patterns such as:

- camelCase
- PascalCase
- snake_case
- kebab-case
- file paths
- abbreviations like API, JWT, DB

## Requirements

The tokenizer should:

- Convert text to lowercase.
- Split punctuation and symbols.
- Split snake_case identifiers.
- Split kebab-case identifiers.
- Split camelCase and PascalCase identifiers.
- Preserve duplicate tokens so ranking can use term frequency.
- Remove very small noisy tokens, such as one-letter variables.

## Examples

getUserById should become:

- get
- user
- by
- id

jwt_token_service should become:

- jwt
- token
- service

RepositoryCrawler should become:

- repository
- crawler

## Design Decision

The tokenizer will not know anything about repositories, files, indexing, or ranking.

Its only job is to convert raw text into a list of searchable tokens.

This keeps the pipeline modular:

crawler -> tokenizer -> indexer -> ranker -> API