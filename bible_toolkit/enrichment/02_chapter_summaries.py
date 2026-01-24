#!/usr/bin/env python3
"""Generate summaries for all Bible chapters using local LLM.

This script populates the bible_chapter_summaries table with:
- Basic info: book, chapter, verse count
- LLM-generated: summary, themes, key verses

Run: uv run python -m bible_toolkit.enrichment.02_chapter_summaries
"""

import json
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from supabase import create_client

from .config import OLLAMA_URL, MODELS, SUPABASE_URL, SUPABASE_KEY, MAX_RETRIES

console = Console()

PROMPT_TEMPLATE = """You are a biblical scholar. Generate a summary for {book} chapter {chapter}.

The chapter contains {verse_count} verses. Here are the first few verses for context:
{sample_verses}

Return ONLY valid JSON:
{{
    "summary": "2-3 sentence summary of what happens in this chapter",
    "themes": ["theme1", "theme2", "theme3"],
    "key_verses": ["{book} {chapter}:X", "{book} {chapter}:Y"]
}}

Be concise. Include 2-4 themes and 2-3 key verses from THIS chapter only.
Return ONLY the JSON."""


def get_chapters_to_process(supabase) -> list[dict]:
    """Get list of all chapters from verse data."""
    result = supabase.table("bible_verses").select("book, chapter").execute()

    # Aggregate unique book/chapter combinations
    chapters = {}
    for row in result.data:
        key = (row["book"], row["chapter"])
        if key not in chapters:
            chapters[key] = {"book": row["book"], "chapter": row["chapter"], "count": 0}
        chapters[key]["count"] += 1

    return sorted(chapters.values(), key=lambda x: (x["book"], x["chapter"]))


def get_sample_verses(supabase, book: str, chapter: int, limit: int = 5) -> str:
    """Get first few verses of a chapter for context."""
    result = (
        supabase.table("bible_verses")
        .select("verse, text")
        .eq("book", book)
        .eq("chapter", chapter)
        .order("verse")
        .limit(limit)
        .execute()
    )

    verses = []
    for row in result.data:
        verses.append(f"v{row['verse']}: {row['text']}")
    return "\n".join(verses)


def generate_chapter_summary(book: str, chapter: int, verse_count: int, sample_verses: str) -> dict:
    """Generate summary for a chapter using Ollama."""
    prompt = PROMPT_TEMPLATE.format(
        book=book,
        chapter=chapter,
        verse_count=verse_count,
        sample_verses=sample_verses,
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODELS["medium"],  # Use medium model for speed
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()["response"]

            # Extract JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])

        except (json.JSONDecodeError, httpx.HTTPError) as e:
            console.print(f"[yellow]Attempt {attempt + 1} failed: {e}[/yellow]")
            if attempt == MAX_RETRIES - 1:
                return {}

    return {}


def main():
    """Generate summaries for all chapters."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY required[/red]")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Get all chapters
    console.print("[blue]Getting chapter list...[/blue]")
    chapters = get_chapters_to_process(supabase)
    console.print(f"[green]Found {len(chapters)} chapters[/green]")

    # Check existing
    existing = supabase.table("bible_chapter_summaries").select("book, chapter").execute()
    existing_keys = {(row["book"], row["chapter"]) for row in existing.data}

    chapters_to_process = [
        c for c in chapters if (c["book"], c["chapter"]) not in existing_keys
    ]

    if len(existing_keys) > 0:
        console.print(f"[yellow]Found {len(existing_keys)} existing summaries.[/yellow]")
        if not chapters_to_process:
            console.print("[green]All chapters already processed![/green]")
            return
        console.print(f"[blue]Processing {len(chapters_to_process)} remaining chapters...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=len(chapters_to_process))

        for ch in chapters_to_process:
            progress.update(task, description=f"[cyan]{ch['book']} {ch['chapter']}[/cyan]")

            # Get sample verses for context
            sample = get_sample_verses(supabase, ch["book"], ch["chapter"])

            # Generate summary
            metadata = generate_chapter_summary(ch["book"], ch["chapter"], ch["count"], sample)

            # Store
            record = {
                "book": ch["book"],
                "chapter": ch["chapter"],
                "verse_count": ch["count"],
                "summary": metadata.get("summary"),
                "themes": metadata.get("themes"),
                "key_verses": metadata.get("key_verses"),
                "enriched_at": "now()",
            }

            supabase.table("bible_chapter_summaries").upsert(
                record, on_conflict="book,chapter"
            ).execute()

            progress.advance(task)

    console.print(f"[bold green]Completed {len(chapters_to_process)} chapters![/bold green]")


if __name__ == "__main__":
    main()
