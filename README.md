# Bible Toolkit

A Python library for accessing enriched Bible data with semantic search, cross-references, and AI-generated insights.

## Features

- **Semantic Search** - Find verses by meaning, not just keywords
- **Cross-References** - 344k verse connections from Treasury of Scripture Knowledge
- **Book Metadata** - Author, theme, summary, key verses for all 66 books
- **Chapter Summaries** - AI-generated summaries for 1,189 chapters
- **Verse Insights** - Explanations and applications for top 500 verses
- **Emotion Tags** - Search verses by emotion (hope, comfort, fear, etc.)

## Installation

```bash
# Add to your project
uv add git+https://github.com/lyzetam/bible-rag.git

# Or with pip
pip install git+https://github.com/lyzetam/bible-rag.git
```

## Quick Start

```python
from bible_toolkit.core import BibleClient

client = BibleClient()

# Semantic search
verses = client.search("feeling anxious", limit=5)
for v in verses:
    print(f"{v['reference']}: {v['text']}")

# Get cross-references
xrefs = client.get_cross_references("Philippians 4:6")

# Get book metadata
book = client.get_book("Philippians")
print(f"Theme: {book['theme']}")

# Get chapter summary
summary = client.get_chapter_summary("Philippians", 4)
print(summary['summary'])

# Search by emotion
hopeful_verses = client.search_by_emotion("hope", limit=10)
```

## Data Overview

| Data | Count | Description |
|------|-------|-------------|
| Verses | 31,100 | Full KJV Bible with 768-dim embeddings |
| Cross-References | 344,799 | Treasury of Scripture Knowledge |
| Books | 66 | Enriched with author, theme, summary |
| Chapter Summaries | 1,189 | AI-generated summaries and themes |
| Verse Insights | 500 | Explanations for top referenced verses |
| Emotion Tags | 31,100 | All verses classified by emotion |

## Configuration

The library works out of the box with the hosted Supabase database. For custom deployments:

```bash
# Optional environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-anon-key
export OLLAMA_URL=http://localhost:11434  # For semantic search
```

## Requirements

- Python 3.10+
- Ollama with `nomic-embed-text` model (for semantic search)
- Network access to Supabase

## Documentation

- [API Reference](docs/api-reference.md) - Complete method documentation
- [Architecture](docs/architecture.md) - System design and data flow
- [Integration Guide](docs/integration-guide.md) - Using in your projects

## CLI Tools

```bash
# Semantic search (requires Ollama)
uv run bible "feeling overwhelmed"

# Emotion search (no Ollama required)
uv run bible -e depression
uv run bible -e anxious
uv run bible --emotions              # List all 87 searchable emotions

# Chat with Bible agent
uv run bible-chat

# Start API server (port 8010)
uv run bible-serve
```

## API Endpoints

```bash
# Start server
uv run bible-serve

# Emotion search (no Ollama required)
curl "http://localhost:8010/emotions/depression?limit=5"

# List available emotions
curl "http://localhost:8010/emotions"

# Semantic search (requires Ollama)
curl "http://localhost:8010/verses/search?query=feeling+anxious&limit=5"

# Get specific verse
curl "http://localhost:8010/verses/John%203:16"
```

## License

Private - Internal use only.
