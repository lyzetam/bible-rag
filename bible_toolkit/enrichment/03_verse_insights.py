#!/usr/bin/env python3
"""Generate detailed insights for most-referenced Bible verses using local LLM.

This script populates the bible_verse_insights table with:
- Explanation of the verse
- Historical context
- Practical application
- Related cross-references

Focuses on the top N most cross-referenced verses.

Run: uv run python -m bible_toolkit.enrichment.03_verse_insights
"""

import json
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from supabase import create_client

from .config import OLLAMA_URL, MODELS, SUPABASE_URL, SUPABASE_KEY, MAX_RETRIES

console = Console()

# Number of top verses to process
TOP_VERSES = 500

PROMPT_TEMPLATE = """You are a biblical scholar. Generate a detailed insight for this verse:

**{reference}**
"{text}"

Return ONLY valid JSON:
{{
    "explanation": "Clear 2-3 sentence explanation of what this verse means",
    "historical_context": "1-2 sentences about the original context (who wrote it, to whom, why)",
    "application": "1-2 sentences on how this applies to modern life",
    "cross_references": ["Reference 1", "Reference 2", "Reference 3"]
}}

Be accurate and pastoral. Include 3-5 genuinely related cross-references.
Return ONLY the JSON."""


def get_top_verses(supabase, limit: int) -> list[dict]:
    """Get the most cross-referenced verses."""
    # Try RPC first (if function exists)
    try:
        result = supabase.rpc(
            "get_top_referenced_verses",
            {"limit_count": limit}
        ).execute()
        if result.data:
            return result.data
    except Exception:
        pass

    # Fallback: manual query with pagination
    console.print("[yellow]Using fallback query for top verses...[/yellow]")
    counts = {}
    offset = 0
    batch_size = 1000

    while True:
        result = (
            supabase.table("bible_cross_references")
            .select("from_reference")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        if not result.data:
            break

        for row in result.data:
            ref = row["from_reference"]
            counts[ref] = counts.get(ref, 0) + 1

        if len(result.data) < batch_size:
            break
        offset += batch_size

    # Get top N
    top_refs = sorted(counts.items(), key=lambda x: -x[1])[:limit]
    return [{"reference": ref, "count": count} for ref, count in top_refs]


def get_verse_text(supabase, reference: str) -> str:
    """Get the text of a verse."""
    result = (
        supabase.table("bible_verses")
        .select("text")
        .eq("reference", reference)
        .limit(1)
        .execute()
    )
    return result.data[0]["text"] if result.data else ""


def generate_insight(reference: str, text: str) -> dict:
    """Generate insight for a verse using Ollama."""
    prompt = PROMPT_TEMPLATE.format(reference=reference, text=text)

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODELS["large"],  # Use large model for quality
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()["response"]

            # Extract JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])

        except (json.JSONDecodeError, httpx.HTTPError) as e:
            console.print(f"[yellow]Attempt {attempt + 1} failed for {reference}: {e}[/yellow]")
            if attempt == MAX_RETRIES - 1:
                return {}

    return {}


def main():
    """Generate insights for top verses."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY required[/red]")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Create helper function if not exists
    try:
        supabase.rpc("get_top_referenced_verses", {"limit_count": 1}).execute()
    except Exception:
        console.print("[blue]Creating helper function...[/blue]")
        # We'll use the fallback method instead

    # Get top verses
    console.print(f"[blue]Getting top {TOP_VERSES} most-referenced verses...[/blue]")
    top_verses = get_top_verses(supabase, TOP_VERSES)
    console.print(f"[green]Found {len(top_verses)} verses to process[/green]")

    # Check existing
    existing = supabase.table("bible_verse_insights").select("reference").execute()
    existing_refs = {row["reference"] for row in existing.data}

    verses_to_process = [v for v in top_verses if v["reference"] not in existing_refs]

    if len(existing_refs) > 0:
        console.print(f"[yellow]Found {len(existing_refs)} existing insights.[/yellow]")
        if not verses_to_process:
            console.print("[green]All top verses already have insights![/green]")
            return
        console.print(f"[blue]Processing {len(verses_to_process)} remaining verses...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=len(verses_to_process))

        for item in verses_to_process:
            ref = item["reference"]
            progress.update(task, description=f"[cyan]{ref}[/cyan]")

            # Get verse text
            text = get_verse_text(supabase, ref)
            if not text:
                console.print(f"[yellow]Skipping {ref} - no text found[/yellow]")
                progress.advance(task)
                continue

            # Generate insight
            insight = generate_insight(ref, text)

            # Store
            record = {
                "reference": ref,
                "explanation": insight.get("explanation"),
                "historical_context": insight.get("historical_context"),
                "application": insight.get("application"),
                "cross_references": insight.get("cross_references"),
                "enriched_at": "now()",
            }

            supabase.table("bible_verse_insights").upsert(
                record, on_conflict="reference"
            ).execute()

            progress.advance(task)

    console.print(f"[bold green]Completed {len(verses_to_process)} verse insights![/bold green]")


if __name__ == "__main__":
    main()
