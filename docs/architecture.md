# Architecture

System design and data flow for Bible Toolkit.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
│                                                                   │
│   from bible_toolkit.core import BibleClient                     │
│   client = BibleClient()                                         │
│   verses = client.search("hope")                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BibleClient                               │
│                     (bible_toolkit/core)                         │
│                                                                   │
│   • Verse operations (search, get, range)                        │
│   • Cross-references                                             │
│   • Book/chapter metadata                                        │
│   • Emotion search                                               │
└─────────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────────┐
        │      Ollama       │   │       Supabase        │
        │  (Embeddings)     │   │     (PostgreSQL)      │
        │                   │   │                       │
        │ nomic-embed-text  │   │  • bible_verses       │
        │ 768 dimensions    │   │  • bible_cross_refs   │
        └───────────────────┘   │  • bible_books        │
                                │  • chapter_summaries  │
                                │  • verse_insights     │
                                │  • emotion_tags       │
                                └───────────────────────┘
```

## Components

### BibleClient (Core Library)

**Location:** `bible_toolkit/core/client.py` (199 lines)

A thin wrapper that:
- Creates embeddings via Ollama for semantic search
- Queries Supabase for Bible data
- Returns raw dictionaries (no transformation)

**Dependencies:**
- `supabase` - Database client
- `httpx` - HTTP client for Ollama
- `pydantic` - Data models (optional)

### Supabase Database

**Project:** `rehpmoxczibgkwcawelo`

| Table | Rows | Description |
|-------|------|-------------|
| `bible_verses` | 31,100 | KJV text + 768-dim embeddings |
| `bible_cross_references` | 344,799 | Verse connections with votes |
| `bible_books` | 66 | Book metadata (enriched) |
| `bible_chapter_summaries` | 1,189 | AI-generated summaries |
| `bible_verse_insights` | 500 | Explanations for top verses |
| `bible_emotion_tags` | 31,100 | Emotion classifications |

### Ollama (Embeddings)

**Model:** `nomic-embed-text`
**Dimensions:** 768
**Purpose:** Convert search queries to vectors for semantic similarity

## Data Flow

### Semantic Search

```
User Query: "feeling anxious"
        │
        ▼
┌───────────────────┐
│  Ollama Embed     │  "feeling anxious" → [0.12, -0.34, ...]
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Supabase RPC     │  search_bible_verses(embedding, threshold, limit)
│  (pgvector)       │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Results          │  Philippians 4:6 (0.82), Matthew 6:34 (0.78), ...
└───────────────────┘
```

### Cross-Reference Lookup

```
Reference: "John 3:16"
        │
        ▼
┌───────────────────┐
│  Supabase Query   │  SELECT to_reference, votes
│                   │  FROM bible_cross_references
│                   │  WHERE from_reference = 'John 3:16'
│                   │  ORDER BY votes DESC
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Results          │  Romans 5:8 (12 votes), 1 John 4:9 (8 votes), ...
└───────────────────┘
```

## Database Schema

### bible_verses

```sql
CREATE TABLE bible_verses (
    id SERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    reference TEXT NOT NULL,      -- "John 3:16"
    text TEXT NOT NULL,
    translation TEXT DEFAULT 'KJV',
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity search
CREATE INDEX idx_verses_embedding
ON bible_verses USING ivfflat (embedding vector_cosine_ops);
```

### bible_cross_references

```sql
CREATE TABLE bible_cross_references (
    id SERIAL PRIMARY KEY,
    from_reference TEXT NOT NULL,  -- "John 3:16"
    to_reference TEXT NOT NULL,    -- "Romans 5:8"
    votes INTEGER DEFAULT 0,       -- Relevance score
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### bible_books

```sql
CREATE TABLE bible_books (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,     -- "Genesis"
    abbreviation TEXT NOT NULL,    -- "Gen"
    testament TEXT NOT NULL,       -- "OT" or "NT"
    position INTEGER NOT NULL,     -- 1-66
    chapters INTEGER NOT NULL,
    verses INTEGER NOT NULL,
    -- Enriched fields (AI-generated)
    author TEXT,
    date_written TEXT,
    audience TEXT,
    theme TEXT,
    summary TEXT,
    outline JSONB,
    key_verses JSONB
);
```

### bible_chapter_summaries

```sql
CREATE TABLE bible_chapter_summaries (
    id SERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_count INTEGER NOT NULL,
    summary TEXT,
    themes JSONB,          -- ["Creation", "Order"]
    key_verses JSONB,      -- ["Genesis 1:1", "Genesis 1:27"]
    UNIQUE(book, chapter)
);
```

### bible_verse_insights

```sql
CREATE TABLE bible_verse_insights (
    id SERIAL PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    explanation TEXT,
    historical_context TEXT,
    application TEXT,
    cross_references JSONB
);
```

### bible_emotion_tags

```sql
CREATE TABLE bible_emotion_tags (
    id SERIAL PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    emotions JSONB NOT NULL,   -- ["hope", "joy"]
    confidence FLOAT
);

-- GIN index for emotion array search
CREATE INDEX idx_emotions_gin ON bible_emotion_tags USING GIN(emotions);
```

## Enrichment Pipeline

Data enrichment runs separately using local LLMs (not part of the client library).

```
┌─────────────────────────────────────────────────────────────┐
│                   Enrichment Scripts                         │
│                (bible_toolkit/enrichment/)                   │
├─────────────────────────────────────────────────────────────┤
│  01_book_metadata.py     │ gemma3:27b  │ 66 books           │
│  02_chapter_summaries.py │ gemma3:27b  │ 1,189 chapters     │
│  03_verse_insights.py    │ gemma3:27b  │ 500 verses         │
│  04_emotion_tags.py      │ gemma3:4b   │ 31,100 verses      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Ollama (Local)   │
                    │  Mac Studio 64GB  │
                    └───────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     Supabase      │
                    │  (Bible Project)  │
                    └───────────────────┘
```

## Data Sources

| Data | Source | License |
|------|--------|---------|
| Bible Text | KJV (1769) | Public Domain |
| Cross-References | Treasury of Scripture Knowledge | Public Domain |
| Embeddings | Generated via Ollama | - |
| Enrichments | Generated via Ollama | - |

## Security

- **Supabase RLS** enabled on all tables
- **Anon key** used (read-only access)
- **No PII** stored
- **Public data** only (KJV is public domain)

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| `search()` | ~200ms | Includes embedding generation |
| `get_verse()` | ~50ms | Direct lookup |
| `get_cross_references()` | ~50ms | Indexed query |
| `get_chapter_summary()` | ~50ms | Direct lookup |
| `search_by_emotion()` | ~100ms | GIN index scan |
