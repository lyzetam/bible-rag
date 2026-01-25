# API Reference

Complete documentation for the `BibleClient` class.

## BibleClient

The main interface for accessing Bible data.

```python
from bible_toolkit.core import BibleClient

client = BibleClient()
```

### Configuration

The client uses these environment variables (all optional with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | Hosted instance | Supabase project URL |
| `SUPABASE_KEY` | Hosted key | Supabase anon key |
| `OLLAMA_URL` | `http://10.85.30.20:11434` | Ollama server for embeddings |

---

## Verse Operations

### search()

Find verses by semantic meaning using vector similarity.

```python
def search(
    query: str,
    limit: int = 5,
    threshold: float = 0.3
) -> list[dict]
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | str | required | Natural language search query |
| `limit` | int | 5 | Maximum results to return |
| `threshold` | float | 0.3 | Minimum similarity score (0-1) |

**Returns:** List of verse dictionaries with similarity scores.

**Example:**
```python
verses = client.search("feeling anxious and worried", limit=5)
for v in verses:
    print(f"{v['reference']} ({v['similarity']:.2f}): {v['text']}")
```

**Response:**
```python
[
    {
        "id": 23145,
        "reference": "Philippians 4:6",
        "text": "Be careful for nothing; but in every thing...",
        "book": "Philippians",
        "chapter": 4,
        "verse": 6,
        "similarity": 0.82
    }
]
```

---

### get_verse()

Get a single verse by reference.

```python
def get_verse(reference: str) -> dict | None
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `reference` | str | Verse reference (e.g., "John 3:16") |

**Returns:** Verse dictionary or `None` if not found.

**Example:**
```python
verse = client.get_verse("John 3:16")
print(verse['text'])
```

---

### get_verses_in_range()

Get multiple verses in a range.

```python
def get_verses_in_range(
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int
) -> list[dict]
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `book` | str | Book name (e.g., "Philippians") |
| `chapter` | int | Chapter number |
| `start_verse` | int | Starting verse number |
| `end_verse` | int | Ending verse number |

**Example:**
```python
verses = client.get_verses_in_range("Philippians", 4, 6, 7)
for v in verses:
    print(f"v{v['verse']}: {v['text']}")
```

---

### get_chapter()

Get all verses in a chapter.

```python
def get_chapter(book: str, chapter: int) -> list[dict]
```

**Example:**
```python
verses = client.get_chapter("Psalm", 23)
for v in verses:
    print(f"{v['verse']}. {v['text']}")
```

---

## Cross-References

### get_cross_references()

Get related verses, ordered by relevance (votes).

```python
def get_cross_references(
    reference: str,
    limit: int = 10
) -> list[dict]
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `reference` | str | required | Source verse reference |
| `limit` | int | 10 | Maximum results |

**Returns:** List of cross-reference dictionaries.

**Example:**
```python
xrefs = client.get_cross_references("John 3:16", limit=5)
for x in xrefs:
    print(f"{x['to_reference']} (votes: {x['votes']})")
```

**Response:**
```python
[
    {"to_reference": "Romans 5:8", "votes": 12},
    {"to_reference": "1 John 4:9", "votes": 8}
]
```

---

## Book Metadata

### get_book()

Get enriched metadata for a Bible book.

```python
def get_book(name: str) -> dict | None
```

**Returns:** Book dictionary with enriched fields.

**Example:**
```python
book = client.get_book("Romans")
print(f"Author: {book['author']}")
print(f"Theme: {book['theme']}")
print(f"Summary: {book['summary']}")
print(f"Key Verses: {book['key_verses']}")
```

**Response:**
```python
{
    "name": "Romans",
    "abbreviation": "Rom",
    "testament": "NT",
    "position": 45,
    "chapters": 16,
    "verses": 433,
    "author": "Paul the Apostle",
    "date_written": "AD 57",
    "audience": "Christians in Rome",
    "theme": "God's righteousness revealed through faith...",
    "summary": "Paul's systematic presentation of the gospel...",
    "outline": ["Introduction (1:1-17)", "Sin (1:18-3:20)", ...],
    "key_verses": ["Romans 1:16", "Romans 3:23", "Romans 8:28"]
}
```

---

### get_all_books()

Get metadata for all 66 books.

```python
def get_all_books() -> list[dict]
```

**Example:**
```python
books = client.get_all_books()
for book in books:
    print(f"{book['position']}. {book['name']} ({book['testament']})")
```

---

## Chapter Summaries

### get_chapter_summary()

Get AI-generated summary for a chapter.

```python
def get_chapter_summary(book: str, chapter: int) -> dict | None
```

**Returns:** Chapter summary dictionary.

**Example:**
```python
summary = client.get_chapter_summary("Genesis", 1)
print(summary['summary'])
print(f"Themes: {summary['themes']}")
print(f"Key Verses: {summary['key_verses']}")
```

**Response:**
```python
{
    "book": "Genesis",
    "chapter": 1,
    "verse_count": 31,
    "summary": "Genesis 1 details God's creation of the heavens...",
    "themes": ["Creation", "Order from Chaos", "Divine Sovereignty"],
    "key_verses": ["Genesis 1:1", "Genesis 1:27"]
}
```

---

## Verse Insights

### get_verse_insight()

Get pre-computed explanation for a frequently-referenced verse.

```python
def get_verse_insight(reference: str) -> dict | None
```

**Returns:** Insight dictionary or `None` (only top 500 verses have insights).

**Example:**
```python
insight = client.get_verse_insight("John 3:16")
if insight:
    print(f"Explanation: {insight['explanation']}")
    print(f"Context: {insight['historical_context']}")
    print(f"Application: {insight['application']}")
```

**Response:**
```python
{
    "reference": "John 3:16",
    "explanation": "This verse summarizes the gospel message...",
    "historical_context": "Jesus spoke these words to Nicodemus...",
    "application": "Believers can have assurance of salvation...",
    "cross_references": ["Romans 5:8", "1 John 4:9"]
}
```

---

## Emotion Tags

### search_by_emotion()

Find verses tagged with a specific emotion.

```python
def search_by_emotion(
    emotion: str,
    limit: int = 10
) -> list[dict]
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `emotion` | str | required | Emotion to search for |
| `limit` | int | 10 | Maximum results |

**Available emotions:** hope, joy, peace, comfort, strength, fear, sorrow, anger, love, gratitude, wisdom, faith

**Example:**
```python
verses = client.search_by_emotion("hope", limit=5)
for v in verses:
    print(f"{v['reference']}: {v['emotions']} ({v['confidence']:.0%})")
```

**Response:**
```python
[
    {
        "reference": "Romans 15:13",
        "emotions": ["hope", "joy", "peace"],
        "confidence": 0.95
    }
]
```

---

## Data Models

The library includes Pydantic models for type safety:

```python
from bible_toolkit.core.models import (
    Verse,
    Book,
    Chapter,
    CrossReference,
    VerseInsight,
    EmotionTag
)
```

See `bible_toolkit/core/models.py` for full model definitions.

---

## Error Handling

The client raises standard exceptions:

| Exception | Cause |
|-----------|-------|
| `ValueError` | Missing required configuration |
| `httpx.HTTPError` | Ollama connection failed |
| `postgrest.APIError` | Supabase query failed |

**Example:**
```python
try:
    verses = client.search("hope")
except httpx.HTTPError:
    print("Ollama not available - check OLLAMA_URL")
```
