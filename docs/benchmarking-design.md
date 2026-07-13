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