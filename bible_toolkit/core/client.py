"""Unified Bible data client."""

import json
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

# Bible Supabase config - use BIBLE_* prefix to avoid conflicts with other Supabase projects
# Uses ONLY BIBLE_SUPABASE_URL or hardcoded default - ignores generic SUPABASE_URL
# This prevents conflicts when the Bible toolkit is used alongside other Supabase projects
BIBLE_SUPABASE_URL_DEFAULT = "https://rehpmoxczibgkwcawelo.supabase.co"
BIBLE_SUPABASE_KEY_DEFAULT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlaHBtb3hjemliZ2t3Y2F3ZWxvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyOTM3NTksImV4cCI6MjA4NDg2OTc1OX0.TW6ukZSPs0GqhwiuffIQU-acrdgTjJzToq8d1htgW_g"

SUPABASE_URL = os.getenv("BIBLE_SUPABASE_URL", BIBLE_SUPABASE_URL_DEFAULT)
SUPABASE_KEY = os.getenv("BIBLE_SUPABASE_KEY", BIBLE_SUPABASE_KEY_DEFAULT)
OLLAMA_URL = os.getenv("BIBLE_OLLAMA_URL") or os.getenv("OLLAMA_URL", "http://10.85.30.20:11434")

# Map common search terms to actual emotion tags in the database
EMOTION_SYNONYMS = {
    # Mental health / emotional states
    "depression": ["sorrow", "despair", "sadness", "grief", "discouragement", "anguish", "hopelessness"],
    "depressed": ["sorrow", "despair", "sadness", "grief", "discouragement", "anguish"],
    "anxiety": ["anxiety", "fear", "worry", "concern", "dread", "panic"],
    "anxious": ["anxiety", "fear", "worry", "concern", "nervousness"],
    "worried": ["worry", "anxiety", "fear", "concern", "uncertainty"],
    "worry": ["worry", "anxiety", "fear", "concern"],
    "stressed": ["anxiety", "pressure", "overwhelm", "burden", "weariness"],
    "stress": ["anxiety", "pressure", "overwhelm", "burden"],
    "overwhelmed": ["overwhelm", "desperation", "weakness", "burden", "weariness"],
    "burnout": ["weariness", "exhaustion", "weakness", "discouragement"],
    "panic": ["panic", "fear", "terror", "anxiety", "dread"],

    # Sadness spectrum
    "sad": ["sorrow", "sadness", "grief", "mourning", "lamentation"],
    "sadness": ["sorrow", "sadness", "grief", "mourning"],
    "grief": ["grief", "sorrow", "mourning", "lamentation", "loss"],
    "grieving": ["grief", "sorrow", "mourning", "lamentation"],
    "mourning": ["mourning", "grief", "sorrow", "lamentation", "loss"],
    "heartbroken": ["grief", "sorrow", "anguish", "pain", "loss"],
    "hurt": ["pain", "sorrow", "anguish", "suffering"],
    "pain": ["pain", "suffering", "anguish", "sorrow"],
    "suffering": ["suffering", "pain", "anguish", "distress"],

    # Fear spectrum
    "scared": ["fear", "terror", "dread", "panic", "anxiety"],
    "afraid": ["fear", "dread", "terror", "anxiety"],
    "fear": ["fear", "dread", "terror", "anxiety", "foreboding"],
    "terrified": ["terror", "fear", "dread", "panic", "horror"],
    "frightened": ["fear", "terror", "dread", "alarm"],

    # Anger spectrum
    "angry": ["anger", "rage", "wrath", "fury", "indignation"],
    "anger": ["anger", "rage", "wrath", "fury"],
    "mad": ["anger", "rage", "frustration", "irritation"],
    "furious": ["fury", "rage", "anger", "wrath"],
    "frustrated": ["frustration", "anger", "irritation", "disappointment"],
    "annoyed": ["irritation", "annoyance", "frustration", "displeasure"],
    "bitter": ["bitterness", "resentment", "anger", "disappointment"],
    "resentful": ["resentment", "bitterness", "anger"],

    # Positive emotions
    "happy": ["joy", "happiness", "gladness", "delight", "contentment"],
    "happiness": ["joy", "happiness", "gladness", "delight"],
    "joy": ["joy", "gladness", "delight", "happiness", "rejoicing"],
    "joyful": ["joy", "gladness", "delight", "happiness"],
    "peaceful": ["peace", "calm", "serenity", "tranquility", "rest"],
    "peace": ["peace", "calm", "serenity", "rest", "comfort"],
    "calm": ["peace", "calm", "serenity", "rest"],
    "content": ["contentment", "peace", "satisfaction", "rest"],
    "grateful": ["gratitude", "thankfulness", "appreciation"],
    "thankful": ["gratitude", "thankfulness", "appreciation", "thanksgiving"],
    "hopeful": ["hope", "expectation", "anticipation", "optimism"],
    "hope": ["hope", "expectation", "anticipation", "promise"],
    "loved": ["love", "affection", "compassion", "care"],
    "love": ["love", "affection", "compassion", "devotion"],
    "comforted": ["comfort", "peace", "consolation", "relief"],
    "relieved": ["relief", "comfort", "peace", "gratitude"],

    # Spiritual emotions
    "faithful": ["faith", "trust", "devotion", "belief"],
    "faith": ["faith", "trust", "belief", "devotion"],
    "doubtful": ["doubt", "uncertainty", "questioning", "confusion"],
    "doubt": ["doubt", "uncertainty", "questioning", "disbelief"],
    "guilty": ["guilt", "shame", "remorse", "regret"],
    "shame": ["shame", "guilt", "humiliation", "remorse"],
    "forgiven": ["forgiveness", "grace", "mercy", "redemption"],
    "repentant": ["repentance", "remorse", "guilt", "sorrow"],

    # Loneliness / isolation
    "lonely": ["loneliness", "isolation", "abandonment", "alienation"],
    "alone": ["loneliness", "isolation", "abandonment"],
    "abandoned": ["abandonment", "loneliness", "rejection", "isolation"],
    "rejected": ["rejection", "abandonment", "loneliness", "hurt"],
    "isolated": ["isolation", "loneliness", "abandonment", "alienation"],

    # Strength / weakness
    "weak": ["weakness", "vulnerability", "helplessness", "powerlessness"],
    "weakness": ["weakness", "vulnerability", "helplessness"],
    "strong": ["strength", "courage", "determination", "power"],
    "strength": ["strength", "courage", "determination", "power"],
    "brave": ["courage", "strength", "determination", "boldness"],
    "courageous": ["courage", "strength", "bravery", "determination"],
    "tired": ["weariness", "weakness", "exhaustion", "fatigue"],
    "exhausted": ["weariness", "exhaustion", "weakness", "fatigue"],

    # Confusion / clarity
    "confused": ["confusion", "uncertainty", "perplexity", "doubt"],
    "lost": ["confusion", "uncertainty", "loneliness", "despair"],
    "uncertain": ["uncertainty", "doubt", "confusion", "questioning"],
    "clear": ["clarity", "understanding", "wisdom", "discernment"],

    # Encouragement / discouragement
    "encouraged": ["encouragement", "hope", "strength", "comfort"],
    "discouraged": ["discouragement", "disappointment", "despair", "hopelessness"],
    "hopeless": ["despair", "hopelessness", "discouragement", "anguish"],
    "motivated": ["encouragement", "determination", "zeal", "enthusiasm"],

    # Trust / betrayal
    "trusting": ["trust", "faith", "confidence", "reliance"],
    "betrayed": ["betrayal", "hurt", "anger", "disappointment"],
    "disappointed": ["disappointment", "discouragement", "sorrow", "frustration"],

    # Wisdom / guidance
    "wise": ["wisdom", "understanding", "discernment", "knowledge"],
    "guidance": ["guidance", "wisdom", "direction", "counsel"],
    "seeking": ["seeking", "searching", "longing", "desire"],

    # Reverence / worship
    "humble": ["humility", "submission", "reverence", "meekness"],
    "awe": ["awe", "wonder", "reverence", "amazement"],
    "worship": ["worship", "praise", "adoration", "reverence"],
}


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

    def search_by_emotion(
        self, emotion: str, limit: int = 10, expand_synonyms: bool = True
    ) -> list[dict]:
        """Find verses tagged with a specific emotion.

        Args:
            emotion: The emotion to search for (e.g., "depression", "anxious", "hope")
            limit: Maximum number of results to return
            expand_synonyms: If True, expands common terms to related emotions
                            (e.g., "depression" -> sorrow, despair, sadness, etc.)

        Returns:
            List of matching verse tags with reference, emotions, and confidence
        """
        search_emotions = self._expand_emotion(emotion) if expand_synonyms else [emotion.lower()]

        # Query for any of the expanded emotions
        all_results = []
        seen_refs = set()

        for emo in search_emotions:
            # Use filter with proper JSON array syntax for JSONB contains
            result = (
                self.db.table("bible_emotion_tags")
                .select("reference, emotions, confidence")
                .filter("emotions", "cs", json.dumps([emo]))
                .order("confidence", desc=True)
                .limit(limit * 2)  # Get more to allow deduplication
                .execute()
            )
            for row in result.data:
                if row["reference"] not in seen_refs:
                    seen_refs.add(row["reference"])
                    all_results.append(row)

        # Sort by confidence and limit
        all_results.sort(key=lambda x: x["confidence"], reverse=True)
        return all_results[:limit]

    def _expand_emotion(self, emotion: str) -> list[str]:
        """Expand an emotion query to include synonyms.

        Args:
            emotion: User's search term (e.g., "depression", "worried")

        Returns:
            List of actual emotion tags to search for
        """
        emotion_lower = emotion.lower().strip()

        # Check if it's a known synonym
        if emotion_lower in EMOTION_SYNONYMS:
            return EMOTION_SYNONYMS[emotion_lower]

        # Return as-is if it's a direct emotion tag
        return [emotion_lower]

    def get_emotion_synonyms(self, emotion: str) -> list[str]:
        """Get the list of emotion tags that a search term maps to.

        Useful for showing users what emotions will be searched.
        """
        return self._expand_emotion(emotion)

    def get_available_emotions(self) -> list[str]:
        """Get list of searchable emotion terms (including synonyms)."""
        return sorted(EMOTION_SYNONYMS.keys())

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
