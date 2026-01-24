"""Unified Bible data client."""

import os
from functools import lru_cache
from pathlib import Path

import httpx
from supabase import Client, create_client

from .models import Verse, Book, Chapter, CrossReference, VerseInsight, EmotionTag

# Load .env file if present
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zzdwykxtcxcahxtzojtw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.85.30.20:11434")


@lru_cache
def get_supabase_client() -> Client:
    """Get singleton Supabase client."""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable required")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


class BibleClient:
    """Unified client for accessing Bible data.

    Example:
        client = BibleClient()
        verses = client.search("feeling anxious", limit=5)
        xrefs = client.get_cross_references("Philippians 4:6")
        book = client.get_book("Philippians")
    """

    def __init__(self):
        self.db = get_supabase_client()
        self.ollama_url = OLLAMA_URL

    # === Verse Operations ===

    def search(self, query: str, limit: int = 5, threshold: float = 0.3) -> list[dict]:
        """Semantic search for verses matching a query."""
        embedding = self._embed(query)
        result = self.db.rpc(
            "search_bible_verses",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()
        return result.data

    def get_verse(self, reference: str) -> dict | None:
        """Get a verse by reference (e.g., 'John 3:16')."""
        result = (
            self.db.table("bible_verses")
            .select("*")
            .eq("reference", reference)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_verses_in_range(
        self, book: str, chapter: int, start_verse: int, end_verse: int
    ) -> list[dict]:
        """Get verses in a range (e.g., Philippians 4:6-7)."""
        result = (
            self.db.table("bible_verses")
            .select("reference, text, verse")
            .eq("book", book)
            .eq("chapter", chapter)
            .gte("verse", start_verse)
            .lte("verse", end_verse)
            .order("verse")
            .execute()
        )
        return result.data

    def get_chapter(self, book: str, chapter: int) -> list[dict]:
        """Get all verses in a chapter."""
        result = (
            self.db.table("bible_verses")
            .select("reference, text, verse")
            .eq("book", book)
            .eq("chapter", chapter)
            .order("verse")
            .execute()
        )
        return result.data

    # === Cross References ===

    def get_cross_references(self, reference: str, limit: int = 10) -> list[dict]:
        """Get cross-references for a verse, ordered by relevance."""
        result = (
            self.db.table("bible_cross_references")
            .select("to_reference, votes")
            .eq("from_reference", reference)
            .order("votes", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # === Book Metadata ===

    def get_book(self, name: str) -> dict | None:
        """Get book metadata (if enriched)."""
        result = (
            self.db.table("bible_books")
            .select("*")
            .eq("name", name)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_all_books(self) -> list[dict]:
        """Get all book metadata."""
        result = (
            self.db.table("bible_books")
            .select("*")
            .order("position")
            .execute()
        )
        return result.data

    # === Chapter Summaries ===

    def get_chapter_summary(self, book: str, chapter: int) -> dict | None:
        """Get chapter summary (if enriched)."""
        result = (
            self.db.table("bible_chapter_summaries")
            .select("*")
            .eq("book", book)
            .eq("chapter", chapter)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # === Verse Insights ===

    def get_verse_insight(self, reference: str) -> dict | None:
        """Get pre-computed insight for a verse."""
        result = (
            self.db.table("bible_verse_insights")
            .select("*")
            .eq("reference", reference)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # === Emotion Tags ===

    def search_by_emotion(self, emotion: str, limit: int = 10) -> list[dict]:
        """Find verses tagged with a specific emotion."""
        result = (
            self.db.table("bible_emotion_tags")
            .select("reference, emotions, confidence")
            .contains("emotions", [emotion])
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # === Embedding ===

    def _embed(self, text: str) -> list[float]:
        """Create embedding using Ollama."""
        response = httpx.post(
            f"{self.ollama_url}/api/embed",
            json={"model": "nomic-embed-text", "input": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Create embeddings for multiple texts."""
        response = httpx.post(
            f"{self.ollama_url}/api/embed",
            json={"model": "nomic-embed-text", "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embeddings"]
