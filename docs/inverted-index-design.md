# Inverted Index Design

## Problem

The search engine needs a fast way to find which files contain a given search term.

Scanning every file for every query is inefficient. Instead, we will build an inverted index.

## Concept

A normal document store maps:

document -> tokens

An inverted index maps:

token -> documents containing that token

## Example

If auth.py contains:

jwt token validate

And user.py contains:

user id validate

The inverted index stores:

jwt -> auth.py
token -> auth.py
validate -> auth.py, user.py
user -> user.py
id -> user.py

## Requirements

The index should track:

- which documents contain each token
- how often each token appears in each document
- which line numbers contain each token
- total number of indexed documents
- document metadata such as relative path and total token count

## Design Decision

This first version will be in-memory.

That means the index is stored in Python dictionaries instead of PostgreSQL.

This is intentional because we first want to prove the search logic clearly before adding persistence.

Later, we can move this structure into PostgreSQL tables.

## Why This Matters

The inverted index is the core data structure behind traditional search engines.

It allows the system to answer:

"Which files contain this token?"

without scanning every file every time.