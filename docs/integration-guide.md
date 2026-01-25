# Integration Guide

How to use Bible Toolkit in your projects.

## Installation

### Using uv (recommended)

```bash
uv add git+https://github.com/lyzetam/bible-rag.git
```

### Using pip

```bash
pip install git+https://github.com/lyzetam/bible-rag.git
```

### For development (editable)

```bash
uv add --editable ~/second-brain/dev/bible-rag
```

## Prerequisites

### Ollama

Semantic search requires Ollama with the embedding model:

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the embedding model
ollama pull nomic-embed-text

# Start Ollama server
ollama serve
```

If Ollama runs on a different machine:

```bash
export OLLAMA_URL=http://your-ollama-server:11434
```

## Basic Usage

```python
from bible_toolkit.core import BibleClient

# Initialize (uses default Supabase instance)
client = BibleClient()

# Search by meaning
verses = client.search("need strength and courage", limit=5)

# Get a specific verse
verse = client.get_verse("Joshua 1:9")

# Get related verses
xrefs = client.get_cross_references("Joshua 1:9")
```

## Common Patterns

### Building a Devotional App

```python
from bible_toolkit.core import BibleClient

client = BibleClient()

def get_daily_verse(mood: str) -> dict:
    """Get a verse matching the user's mood."""
    verses = client.search_by_emotion(mood, limit=1)
    if verses:
        ref = verses[0]['reference']
        verse = client.get_verse(ref)
        insight = client.get_verse_insight(ref)
        return {
            "verse": verse,
            "insight": insight,
            "related": client.get_cross_references(ref, limit=3)
        }
    return None

# Usage
result = get_daily_verse("hope")
print(f"{result['verse']['reference']}: {result['verse']['text']}")
if result['insight']:
    print(f"Application: {result['insight']['application']}")
```

### Building a Bible Study Tool

```python
from bible_toolkit.core import BibleClient

client = BibleClient()

def get_chapter_study(book: str, chapter: int) -> dict:
    """Get everything needed for chapter study."""
    return {
        "verses": client.get_chapter(book, chapter),
        "summary": client.get_chapter_summary(book, chapter),
        "book_context": client.get_book(book)
    }

# Usage
study = get_chapter_study("Romans", 8)
print(f"Chapter Theme: {study['summary']['themes']}")
print(f"Book Theme: {study['book_context']['theme']}")
```

### Building a RAG Agent

```python
from bible_toolkit.core import BibleClient
from langchain_anthropic import ChatAnthropic

client = BibleClient()
llm = ChatAnthropic(model="claude-sonnet-4-20250514")

def answer_question(question: str) -> str:
    """Answer a question using Bible context."""
    # Get relevant verses
    verses = client.search(question, limit=5)

    # Build context
    context = "\n".join([
        f"{v['reference']}: {v['text']}"
        for v in verses
    ])

    # Add cross-references for depth
    if verses:
        xrefs = client.get_cross_references(verses[0]['reference'])
        for xref in xrefs[:3]:
            ref_verse = client.get_verse(xref['to_reference'])
            if ref_verse:
                context += f"\n{ref_verse['reference']}: {ref_verse['text']}"

    # Generate answer
    prompt = f"""Based on these Bible verses, answer the question.

Verses:
{context}

Question: {question}

Answer:"""

    return llm.invoke(prompt).content

# Usage
answer = answer_question("How can I find peace when anxious?")
```

### Building an API

```python
from fastapi import FastAPI
from bible_toolkit.core import BibleClient

app = FastAPI()
client = BibleClient()

@app.get("/search")
def search(q: str, limit: int = 5):
    return client.search(q, limit=limit)

@app.get("/verse/{reference}")
def get_verse(reference: str):
    return client.get_verse(reference)

@app.get("/book/{name}")
def get_book(name: str):
    return client.get_book(name)

@app.get("/emotions/{emotion}")
def search_emotion(emotion: str, limit: int = 10):
    return client.search_by_emotion(emotion, limit=limit)
```

## Error Handling

```python
from bible_toolkit.core import BibleClient
import httpx

client = BibleClient()

def safe_search(query: str) -> list:
    """Search with error handling."""
    try:
        return client.search(query)
    except httpx.ConnectError:
        print("Ollama not available - using fallback")
        # Fallback: search by exact text match
        return []
    except Exception as e:
        print(f"Search failed: {e}")
        return []
```

## Testing

```python
import pytest
from bible_toolkit.core import BibleClient

@pytest.fixture
def client():
    return BibleClient()

def test_get_verse(client):
    verse = client.get_verse("John 3:16")
    assert verse is not None
    assert "God so loved" in verse['text']

def test_search(client):
    verses = client.search("hope", limit=3)
    assert len(verses) <= 3
    assert all('reference' in v for v in verses)

def test_cross_references(client):
    xrefs = client.get_cross_references("John 3:16")
    assert len(xrefs) > 0
    assert all('to_reference' in x for x in xrefs)
```

## Performance Tips

### Cache the client

```python
from functools import lru_cache
from bible_toolkit.core import BibleClient

@lru_cache
def get_client() -> BibleClient:
    return BibleClient()

# Use in your app
client = get_client()
```

### Batch operations

```python
# Instead of multiple calls:
for ref in references:
    verse = client.get_verse(ref)  # N database calls

# Use range queries when possible:
verses = client.get_chapter("Romans", 8)  # 1 database call
```

### Pre-fetch cross-references

```python
def get_verse_with_context(reference: str) -> dict:
    """Get verse with pre-fetched related content."""
    verse = client.get_verse(reference)
    if not verse:
        return None

    return {
        "verse": verse,
        "insight": client.get_verse_insight(reference),
        "cross_refs": client.get_cross_references(reference, limit=5),
        "chapter_summary": client.get_chapter_summary(
            verse['book'], verse['chapter']
        )
    }
```

## Troubleshooting

### "Ollama connection failed"

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check model is available
ollama list | grep nomic-embed-text

# Set correct URL if remote
export OLLAMA_URL=http://10.85.30.20:11434
```

### "Supabase query failed"

```bash
# Check network connectivity
curl https://rehpmoxczibgkwcawelo.supabase.co/rest/v1/

# Override credentials if needed
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_KEY=your-anon-key
```

### "No results from search"

1. Check Ollama is running and has `nomic-embed-text`
2. Lower the threshold: `client.search(query, threshold=0.2)`
3. Try simpler queries: "hope" instead of "hoping for better days"
