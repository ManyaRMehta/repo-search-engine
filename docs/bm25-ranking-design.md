# BM25 Ranking Design

## Problem

The inverted index can find documents that contain query terms, but it does not know how to rank those documents.

For example, if a user searches for "jwt token", many files may match. The search engine needs to decide which file should appear first.

## Why Not Simple Keyword Counting?

A simple keyword count has problems:

- It rewards very long files too much.
- It does not account for whether a term is rare or common.
- It cannot distinguish between a highly relevant short file and a huge file with scattered matches.

## BM25

BM25 is a traditional ranking algorithm used in information retrieval.

It considers:

- term frequency: how often a query term appears in a document
- document frequency: how many documents contain the term
- document length: how long the document is compared to the average document

## Design Decision

This project will implement BM25 manually instead of relying on Elasticsearch or a library.

This makes the ranking logic easier to explain in technical interviews and demonstrates understanding of search internals.

## Inputs

The BM25 ranker needs:

- query tokens
- inverted index postings
- total number of documents
- document frequency for each query term
- document token counts
- average document length

## Output

The ranker returns search results ordered by descending BM25 score.

Each result should include:

- document id
- relative path
- score
- matched tokens
- matching line numbers