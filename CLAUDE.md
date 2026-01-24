# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Load Bible into Supabase (one-time, ~31k verses)
uv run bible-load

# Query verses (CLI)
uv run bible "feeling overwhelmed"
uv run bible                          # Interactive mode

# Chat with AI agent
uv run bible-chat                     # Default: companion persona
uv run bible-chat --persona preacher  # Preacher persona

# Run API server (port 8010)
uv run bible-serve
```

## Environment Variables

Required in `.env`:
- `SUPABASE_KEY` - Supabase anon/service key (Phoenix project)
- `ANTHROPIC_API_KEY` - Required for agent and API

Optional:
- `SUPABASE_URL` - Defaults to Phoenix project URL

Ollama must be running with `nomic-embed-text` model for embeddings.

## Architecture

```
bible_rag/
├── load.py           # One-time: Download KJV, embed, upload to Supabase
├── query.py          # CLI semantic search (standalone, no LLM)
├── agent/            # LangGraph agent with conversation memory
│   ├── factory.py    # Agent creation (uses Claude + MemorySaver)
│   ├── tools.py      # 4 tools: search_bible_verses, search_curated_verses,
│   │                 #          get_verse_context, get_verse_by_reference
│   └── prompts.py    # Persona system prompts (companion, preacher)
├── api/              # FastAPI server
│   └── app.py        # POST /chat, GET /verses/search, GET /verses/{ref}
├── services/
│   └── bible.py      # BibleService: Supabase client wrapper
└── data/
    └── curated_verses.py  # Hand-picked emotion-to-verse mappings
```

## Data Flow

1. **Embedding**: User query -> Ollama `nomic-embed-text` -> 768-dim vector
2. **Search**: Vector -> Supabase RPC `search_bible_verses` (pgvector cosine similarity)
3. **Agent**: LangGraph ReAct agent decides which tools to call based on user message

## Supabase Schema

Uses Phoenix project (`zzdwykxtcxcahxtzojtw`). Table `bible_verses`:
- `book`, `chapter`, `verse`, `reference`, `text`, `translation`
- `embedding` (vector 768)

Requires RPC function `search_bible_verses(query_embedding, match_threshold, match_count)`.

## Agent Personas

- **companion** (default): Empathetic listener, validates feelings first, gentle Scripture sharing
- **preacher**: Modern, relatable, connects ancient text to contemporary life

Both personas are instructed to always use tools for verses (never quote from memory).
