#!/usr/bin/env python3
"""Tag all Bible verses with emotions using local LLM.

This script populates the bible_emotion_tags table with:
- Emotion classifications for each verse
- Confidence scores

Run: uv run python -m bible_toolkit.enrichment.04_emotion_tags
"""

import json
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from supabase import create_client

from .config import OLLAMA_URL, MODELS, SUPABASE_URL, SUPABASE_KEY, BATCH_SIZE

console = Console()

# Emotions to classify
EMOTIONS = [
    "hope", "fear", "joy", "sorrow", "peace", "anxiety",
    "love", "anger", "gratitude", "guilt", "comfort", "loneliness",
    "strength", "weakness", "faith", "doubt", "forgiveness", "judgment",
    "encouragement", "warning", "wisdom", "promise"
]

PROMPT_TEMPLATE = """Classify the emotions in these Bible verses. For each verse, identify the dominant emotions from this list:
{emotions}

Verses:
{verses}

Return ONLY valid JSON array:
[
    {{"reference": "Book Chapter:Verse", "emotions": ["emotion1", "emotion2"], "confidence": 0.85}},
    ...
]

Rules:
- Pick 1-3 most relevant emotions per verse
- Confidence: 0.9+ = very clear, 0.7-0.9 = moderate, 0.5-0.7 = subtle
- Return ONLY the JSON array, no other text"""


def get_verses_batch(supabase, offset: int, limit: int) -> list[dict]:
    """Get a batch of verses."""
    result = (
        supabase.table("bible_verses")
        .select("reference, text")
        .order("id")
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


def classify_batch(verses: list[dict]) -> list[dict]:
    """Classify emotions for a batch of verses."""
    verses_text = "\n".join(
        f"- {v['reference']}: {v['text'][:200]}" for v in verses
    )

    prompt = PROMPT_TEMPLATE.format(
        emotions=", ".join(EMOTIONS),
        verses=verses_text,
    )

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODELS["small"],  # Fast model for classification
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()["response"]

        # Extract JSON array
        start = result.find("[")
        end = result.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])

    except (json.JSONDecodeError, httpx.HTTPError) as e:
        console.print(f"[yellow]Batch failed: {e}[/yellow]")

    return []


def main():
    """Tag all verses with emotions."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY required[/red]")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get total verse count
    total = supabase.table("bible_verses").select("id", count="exact").execute()
    total_verses = total.count

    # Check existing
    existing = supabase.table("bible_emotion_tags").select("id", count="exact").execute()
    existing_count = existing.count or 0

    if existing_count > 0:
        console.print(f"[yellow]Found {existing_count} existing tags. Continuing...[/yellow]")
        if existing_count >= total_verses:
            console.print("[green]All verses already tagged![/green]")
            return
        # Auto-continue from where we left off (no prompt for background jobs)
        tagged_refs = set()
        offset = 0
        while True:
            tagged = supabase.table("bible_emotion_tags").select("reference").range(offset, offset + 999).execute()
            if not tagged.data:
                break
            tagged_refs.update(row["reference"] for row in tagged.data)
            if len(tagged.data) < 1000:
                break
            offset += 1000
    else:
        tagged_refs = set()

    console.print(f"[blue]Processing {total_verses} verses in batches of {BATCH_SIZE}...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Tagging...", total=total_verses)
        progress.update(task, completed=len(tagged_refs))

        offset = 0
        while offset < total_verses:
            # Get batch
            verses = get_verses_batch(supabase, offset, BATCH_SIZE)
            if not verses:
                break

            # Filter out already tagged
            verses_to_tag = [v for v in verses if v["reference"] not in tagged_refs]

            if verses_to_tag:
                # Classify
                results = classify_batch(verses_to_tag)

                # Store
                for item in results:
                    if item.get("reference") and item.get("emotions"):
                        record = {
                            "reference": item["reference"],
                            "emotions": item["emotions"],
                            "confidence": item.get("confidence", 0.7),
                        }
                        try:
                            supabase.table("bible_emotion_tags").upsert(
                                record, on_conflict="reference"
                            ).execute()
                        except Exception as e:
                            console.print(f"[red]Error storing {item['reference']}: {e}[/red]")

            progress.update(task, advance=len(verses))
            offset += BATCH_SIZE

    console.print("[bold green]Emotion tagging complete![/bold green]")


if __name__ == "__main__":
    main()
