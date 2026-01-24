#!/usr/bin/env python3
"""Generate metadata for all 66 Bible books using local LLM.

This script populates the bible_books table with:
- Basic info: name, testament, position, chapter/verse counts
- LLM-generated: author, date, audience, theme, summary, outline, key verses

Run: uv run python -m bible_toolkit.enrichment.01_book_metadata
"""

import json
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from supabase import create_client

from .config import OLLAMA_URL, MODELS, SUPABASE_URL, SUPABASE_KEY, MAX_RETRIES

console = Console()

# All 66 books with basic metadata
BOOKS = [
    # Old Testament (39 books)
    {"name": "Genesis", "abbr": "Gen", "testament": "OT", "pos": 1},
    {"name": "Exodus", "abbr": "Exod", "testament": "OT", "pos": 2},
    {"name": "Leviticus", "abbr": "Lev", "testament": "OT", "pos": 3},
    {"name": "Numbers", "abbr": "Num", "testament": "OT", "pos": 4},
    {"name": "Deuteronomy", "abbr": "Deut", "testament": "OT", "pos": 5},
    {"name": "Joshua", "abbr": "Josh", "testament": "OT", "pos": 6},
    {"name": "Judges", "abbr": "Judg", "testament": "OT", "pos": 7},
    {"name": "Ruth", "abbr": "Ruth", "testament": "OT", "pos": 8},
    {"name": "1 Samuel", "abbr": "1Sam", "testament": "OT", "pos": 9},
    {"name": "2 Samuel", "abbr": "2Sam", "testament": "OT", "pos": 10},
    {"name": "1 Kings", "abbr": "1Kgs", "testament": "OT", "pos": 11},
    {"name": "2 Kings", "abbr": "2Kgs", "testament": "OT", "pos": 12},
    {"name": "1 Chronicles", "abbr": "1Chr", "testament": "OT", "pos": 13},
    {"name": "2 Chronicles", "abbr": "2Chr", "testament": "OT", "pos": 14},
    {"name": "Ezra", "abbr": "Ezra", "testament": "OT", "pos": 15},
    {"name": "Nehemiah", "abbr": "Neh", "testament": "OT", "pos": 16},
    {"name": "Esther", "abbr": "Esth", "testament": "OT", "pos": 17},
    {"name": "Job", "abbr": "Job", "testament": "OT", "pos": 18},
    {"name": "Psalms", "abbr": "Ps", "testament": "OT", "pos": 19},
    {"name": "Proverbs", "abbr": "Prov", "testament": "OT", "pos": 20},
    {"name": "Ecclesiastes", "abbr": "Eccl", "testament": "OT", "pos": 21},
    {"name": "Song of Solomon", "abbr": "Song", "testament": "OT", "pos": 22},
    {"name": "Isaiah", "abbr": "Isa", "testament": "OT", "pos": 23},
    {"name": "Jeremiah", "abbr": "Jer", "testament": "OT", "pos": 24},
    {"name": "Lamentations", "abbr": "Lam", "testament": "OT", "pos": 25},
    {"name": "Ezekiel", "abbr": "Ezek", "testament": "OT", "pos": 26},
    {"name": "Daniel", "abbr": "Dan", "testament": "OT", "pos": 27},
    {"name": "Hosea", "abbr": "Hos", "testament": "OT", "pos": 28},
    {"name": "Joel", "abbr": "Joel", "testament": "OT", "pos": 29},
    {"name": "Amos", "abbr": "Amos", "testament": "OT", "pos": 30},
    {"name": "Obadiah", "abbr": "Obad", "testament": "OT", "pos": 31},
    {"name": "Jonah", "abbr": "Jonah", "testament": "OT", "pos": 32},
    {"name": "Micah", "abbr": "Mic", "testament": "OT", "pos": 33},
    {"name": "Nahum", "abbr": "Nah", "testament": "OT", "pos": 34},
    {"name": "Habakkuk", "abbr": "Hab", "testament": "OT", "pos": 35},
    {"name": "Zephaniah", "abbr": "Zeph", "testament": "OT", "pos": 36},
    {"name": "Haggai", "abbr": "Hag", "testament": "OT", "pos": 37},
    {"name": "Zechariah", "abbr": "Zech", "testament": "OT", "pos": 38},
    {"name": "Malachi", "abbr": "Mal", "testament": "OT", "pos": 39},
    # New Testament (27 books)
    {"name": "Matthew", "abbr": "Matt", "testament": "NT", "pos": 40},
    {"name": "Mark", "abbr": "Mark", "testament": "NT", "pos": 41},
    {"name": "Luke", "abbr": "Luke", "testament": "NT", "pos": 42},
    {"name": "John", "abbr": "John", "testament": "NT", "pos": 43},
    {"name": "Acts", "abbr": "Acts", "testament": "NT", "pos": 44},
    {"name": "Romans", "abbr": "Rom", "testament": "NT", "pos": 45},
    {"name": "1 Corinthians", "abbr": "1Cor", "testament": "NT", "pos": 46},
    {"name": "2 Corinthians", "abbr": "2Cor", "testament": "NT", "pos": 47},
    {"name": "Galatians", "abbr": "Gal", "testament": "NT", "pos": 48},
    {"name": "Ephesians", "abbr": "Eph", "testament": "NT", "pos": 49},
    {"name": "Philippians", "abbr": "Phil", "testament": "NT", "pos": 50},
    {"name": "Colossians", "abbr": "Col", "testament": "NT", "pos": 51},
    {"name": "1 Thessalonians", "abbr": "1Thess", "testament": "NT", "pos": 52},
    {"name": "2 Thessalonians", "abbr": "2Thess", "testament": "NT", "pos": 53},
    {"name": "1 Timothy", "abbr": "1Tim", "testament": "NT", "pos": 54},
    {"name": "2 Timothy", "abbr": "2Tim", "testament": "NT", "pos": 55},
    {"name": "Titus", "abbr": "Titus", "testament": "NT", "pos": 56},
    {"name": "Philemon", "abbr": "Phlm", "testament": "NT", "pos": 57},
    {"name": "Hebrews", "abbr": "Heb", "testament": "NT", "pos": 58},
    {"name": "James", "abbr": "Jas", "testament": "NT", "pos": 59},
    {"name": "1 Peter", "abbr": "1Pet", "testament": "NT", "pos": 60},
    {"name": "2 Peter", "abbr": "2Pet", "testament": "NT", "pos": 61},
    {"name": "1 John", "abbr": "1John", "testament": "NT", "pos": 62},
    {"name": "2 John", "abbr": "2John", "testament": "NT", "pos": 63},
    {"name": "3 John", "abbr": "3John", "testament": "NT", "pos": 64},
    {"name": "Jude", "abbr": "Jude", "testament": "NT", "pos": 65},
    {"name": "Revelation", "abbr": "Rev", "testament": "NT", "pos": 66},
]

PROMPT_TEMPLATE = """You are a biblical scholar. Generate metadata for the book of {book_name} in the Bible.

Return ONLY valid JSON with these exact fields:
{{
    "author": "Traditional author (e.g., 'Moses', 'Paul', 'Unknown')",
    "date_written": "Approximate date or range (e.g., '50-60 AD', '1400-1200 BC')",
    "audience": "Original intended audience (e.g., 'Jewish exiles in Babylon', 'Church at Rome')",
    "theme": "One sentence capturing the main theme",
    "summary": "2-3 sentence summary of the book's content and significance",
    "outline": ["Major section 1", "Major section 2", "..."],
    "key_verses": ["Reference 1", "Reference 2", "..."]
}}

Be concise and factual. Include 3-5 outline sections and 3-5 key verses.
Return ONLY the JSON, no other text."""


def generate_book_metadata(book_name: str) -> dict:
    """Generate metadata for a book using Ollama."""
    prompt = PROMPT_TEMPLATE.format(book_name=book_name)

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODELS["large"],
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()["response"]

            # Extract JSON from response
            # Try to find JSON in the response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)

        except (json.JSONDecodeError, httpx.HTTPError) as e:
            console.print(f"[yellow]Attempt {attempt + 1} failed for {book_name}: {e}[/yellow]")
            if attempt == MAX_RETRIES - 1:
                return {}

    return {}


def get_book_stats(supabase, book_name: str) -> tuple[int, int]:
    """Get chapter and verse counts for a book from existing data."""
    # Get chapter count
    chapters = supabase.table("bible_verses").select("chapter").eq("book", book_name).execute()
    unique_chapters = set(row["chapter"] for row in chapters.data)

    # Get verse count
    verses = supabase.table("bible_verses").select("id", count="exact").eq("book", book_name).execute()

    return len(unique_chapters), verses.count or 0


def main():
    """Generate and store metadata for all 66 books."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY required[/red]")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check existing
    existing = supabase.table("bible_books").select("name").execute()
    existing_names = {row["name"] for row in existing.data}

    if existing_names:
        console.print(f"[yellow]Found {len(existing_names)} existing books.[/yellow]")
        if not console.input("Re-generate? [y/N]: ").lower().startswith("y"):
            # Only process missing books
            books_to_process = [b for b in BOOKS if b["name"] not in existing_names]
            if not books_to_process:
                console.print("[green]All books already processed![/green]")
                return
        else:
            books_to_process = BOOKS
    else:
        books_to_process = BOOKS

    console.print(f"[blue]Processing {len(books_to_process)} books...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating...", total=len(books_to_process))

        for book in books_to_process:
            progress.update(task, description=f"[cyan]{book['name']}[/cyan]")

            # Get chapter/verse counts from existing verse data
            chapters, verses = get_book_stats(supabase, book["name"])

            # Generate LLM metadata
            metadata = generate_book_metadata(book["name"])

            # Prepare record
            record = {
                "name": book["name"],
                "abbreviation": book["abbr"],
                "testament": book["testament"],
                "position": book["pos"],
                "chapters": chapters,
                "verses": verses,
                "author": metadata.get("author"),
                "date_written": metadata.get("date_written"),
                "audience": metadata.get("audience"),
                "theme": metadata.get("theme"),
                "summary": metadata.get("summary"),
                "outline": metadata.get("outline"),
                "key_verses": metadata.get("key_verses"),
                "enriched_at": "now()",
            }

            # Upsert
            supabase.table("bible_books").upsert(
                record, on_conflict="name"
            ).execute()

            progress.advance(task)

    console.print(f"[bold green]Completed {len(books_to_process)} books![/bold green]")


if __name__ == "__main__":
    main()
