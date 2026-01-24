"""Bible search service wrapping existing query functionality."""

import os
from functools import lru_cache
from pathlib import Path

import ollama
from supabase import Client, create_client

# Load .env file if present
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zzdwykxtcxcahxtzojtw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


@lru_cache
def get_supabase_client() -> Client:
    """Get singleton Supabase client."""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_KEY environment variable required")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


class BibleService:
    """Service for searching and retrieving Bible verses."""

    def __init__(self):
        self.client = get_supabase_client()

    def search_verses(
        self, query: str, limit: int = 5, threshold: float = 0.3
    ) -> list[dict]:
        """Search for Bible verses matching the query using semantic search."""
        response = ollama.embed(model="nomic-embed-text", input=query)
        query_embedding = response["embeddings"][0]

        result = self.client.rpc(
            "search_bible_verses",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()

        return result.data

    def get_verse_by_reference(self, reference: str) -> dict | None:
        """Get a specific verse by reference (e.g., 'John 3:16')."""
        result = (
            self.client.table("bible_verses")
            .select("*")
            .eq("reference", reference)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_verse_context(
        self, book: str, chapter: int, verse: int, context_size: int = 2
    ) -> list[dict]:
        """Get surrounding verses for context."""
        start_verse = max(1, verse - context_size)
        end_verse = verse + context_size

        result = (
            self.client.table("bible_verses")
            .select("reference, text, verse")
            .eq("book", book)
            .eq("chapter", chapter)
            .gte("verse", start_verse)
            .lte("verse", end_verse)
            .order("verse")
            .execute()
        )
        return result.data

    def get_verses_by_book_chapter(self, book: str, chapter: int) -> list[dict]:
        """Get all verses from a specific chapter."""
        result = (
            self.client.table("bible_verses")
            .select("reference, text, verse")
            .eq("book", book)
            .eq("chapter", chapter)
            .order("verse")
            .execute()
        )
        return result.data

    def get_cross_references(self, reference: str, limit: int = 10) -> list[dict]:
        """Get cross-references for a verse, ordered by relevance (votes)."""
        result = (
            self.client.table("bible_cross_references")
            .select("to_reference, votes")
            .eq("from_reference", reference)
            .order("votes", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
