# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Bible Toolkit is a reusable Bible data library with enrichment tools and a RAG application.

## Structure

```
bible_toolkit/
├── core/                 # Reusable library
│   ├── client.py         # BibleClient: unified data access
│   └── models.py         # Pydantic models (Verse, Book, Chapter, etc.)
│
├── enrichment/           # Batch generation scripts (local LLM)
│   ├── 01_book_metadata.py      # 66 book summaries
│   ├── 02_chapter_summaries.py  # 1,189 chapter summaries
│   ├── 03_verse_insights.py     # Top 500 verse explanations
│   └── 04_emotion_tags.py       # Tag all 31k verses with emotions
│
└── apps/rag/             # (TODO) RAG application

bible_rag/                # Legacy RAG app (being migrated)
├── agent/                # LangGraph agent with tools
├── api/                  # FastAPI server
└── services/             # Bible service wrapper
```

## Commands

```bash
# Install
uv sync

# Data loaders (one-time)
uv run bible-load              # Load 31k verses
uv run bible-load-xrefs        # Load 344k cross-references

# Enrichment (run on Mac Studio via Ollama)
uv run python -m bible_toolkit.enrichment.01_book_metadata
uv run python -m bible_toolkit.enrichment.02_chapter_summaries
uv run python -m bible_toolkit.enrichment.03_verse_insights
uv run python -m bible_toolkit.enrichment.04_emotion_tags

# CLI tools
uv run bible "feeling anxious"
uv run bible-chat --persona companion
uv run bible-serve              # API on port 8010
```

## Environment

```bash
# .env (optional - defaults are built-in)
SUPABASE_URL=https://rehpmoxczibgkwcawelo.supabase.co
SUPABASE_KEY=your_anon_key
OLLAMA_URL=http://10.85.30.20:11434  # Mac Studio
ANTHROPIC_API_KEY=your_key           # For agent
```

## Supabase Project

| Field | Value |
|-------|-------|
| Project | Bible (dedicated) |
| Ref | `rehpmoxczibgkwcawelo` |
| URL | `https://rehpmoxczibgkwcawelo.supabase.co` |

## Database Schema

| Table | Purpose |
|-------|---------|
| `bible_verses` | 31k verses with embeddings (768-dim) |
| `bible_cross_references` | 344k cross-references with votes |
| `bible_books` | 66 books with LLM-generated metadata |
| `bible_chapter_summaries` | 1,189 chapter summaries |
| `bible_verse_insights` | Top 500 verse explanations |
| `bible_emotion_tags` | Emotion classification for all verses |

## Ollama Models (Mac Studio 64GB)

| Task | Model | Size |
|------|-------|------|
| Book metadata, verse insights | gemma3:27b | 17.4GB |
| Chapter summaries | deepseek-r1:14b | 9GB |
| Emotion classification | gemma3:4b | 3.3GB |
| Embeddings | nomic-embed-text | - |

## Using the Library

```python
from bible_toolkit.core import BibleClient

client = BibleClient()

# Semantic search
verses = client.search("feeling anxious", limit=5)

# Get cross-references
xrefs = client.get_cross_references("Philippians 4:6")

# Get book metadata
book = client.get_book("Philippians")

# Search by emotion (after enrichment)
verses = client.search_by_emotion("hope", limit=10)
```
