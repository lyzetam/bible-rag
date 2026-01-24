#!/usr/bin/env python3
"""Load Bible verses into Supabase with embeddings."""

import json
import os
import re
from pathlib import Path

import httpx
import ollama
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from supabase import create_client

# Load .env file if present
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

console = Console()

# Bible JSON source (KJV - public domain)
BIBLE_URL = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
CACHE_PATH = Path(__file__).parent.parent / "data" / "kjv.json"

# Supabase Phoenix project
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zzdwykxtcxcahxtzojtw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # anon key or service key

BATCH_SIZE = 100  # verses per batch for embedding

# Book abbreviation to full name mapping
BOOK_NAMES = {
    "gn": "Genesis", "ex": "Exodus", "lv": "Leviticus", "nm": "Numbers", "dt": "Deuteronomy",
    "js": "Joshua", "jud": "Judges", "rt": "Ruth", "1sm": "1 Samuel", "2sm": "2 Samuel",
    "1kgs": "1 Kings", "2kgs": "2 Kings", "1ch": "1 Chronicles", "2ch": "2 Chronicles",
    "ezr": "Ezra", "ne": "Nehemiah", "et": "Esther", "job": "Job", "ps": "Psalms",
    "prv": "Proverbs", "ecl": "Ecclesiastes", "so": "Song of Solomon", "is": "Isaiah",
    "jr": "Jeremiah", "lm": "Lamentations", "ez": "Ezekiel", "dn": "Daniel", "ho": "Hosea",
    "jl": "Joel", "am": "Amos", "ob": "Obadiah", "jn": "Jonah", "mc": "Micah",
    "na": "Nahum", "hk": "Habakkuk", "zp": "Zephaniah", "hg": "Haggai", "zc": "Zechariah",
    "ml": "Malachi", "mt": "Matthew", "mk": "Mark", "lk": "Luke", "jo": "John",
    "act": "Acts", "rm": "Romans", "1co": "1 Corinthians", "2co": "2 Corinthians",
    "gl": "Galatians", "eph": "Ephesians", "ph": "Philippians", "cl": "Colossians",
    "1ts": "1 Thessalonians", "2ts": "2 Thessalonians", "1tm": "1 Timothy", "2tm": "2 Timothy",
    "tt": "Titus", "phm": "Philemon", "hb": "Hebrews", "jm": "James", "1pe": "1 Peter",
    "2pe": "2 Peter", "1jo": "1 John", "2jo": "2 John", "3jo": "3 John", "jd": "Jude",
    "re": "Revelation",
}


def download_bible() -> list:
    """Download or load cached Bible JSON."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if CACHE_PATH.exists():
        console.print(f"[dim]Loading cached Bible from {CACHE_PATH}[/dim]")
        return json.loads(CACHE_PATH.read_text())

    console.print("[blue]Downloading Bible from GitHub...[/blue]")
    response = httpx.get(BIBLE_URL, timeout=60)
    response.raise_for_status()

    # Remove BOM if present
    text = response.text.lstrip("\ufeff")
    data = json.loads(text)
    CACHE_PATH.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Cached to {CACHE_PATH}[/green]")
    return data


def clean_text(text: str) -> str:
    """Clean verse text by removing Hebrew/Greek annotations."""
    # Remove {annotations} like {the light from...: Heb. between the light}
    text = re.sub(r"\s*\{[^}]+\}", "", text)
    return text.strip()


def parse_bible(data: list) -> list[dict]:
    """Parse Bible JSON into verse records."""
    verses = []

    for book_data in data:
        abbrev = book_data["abbrev"]
        book = BOOK_NAMES.get(abbrev, abbrev.title())

        for chapter_idx, chapter_verses in enumerate(book_data["chapters"], start=1):
            for verse_idx, text in enumerate(chapter_verses, start=1):
                clean = clean_text(text)
                if clean:  # Skip empty verses
                    verses.append({
                        "book": book,
                        "chapter": chapter_idx,
                        "verse": verse_idx,
                        "reference": f"{book} {chapter_idx}:{verse_idx}",
                        "text": clean,
                        "translation": "KJV",
                    })

    return verses


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """Create embeddings using Ollama nomic-embed-text (batched)."""
    response = ollama.embed(model="nomic-embed-text", input=texts)
    return response["embeddings"]


def main():
    """Main loader function."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY environment variable required[/red]")
        console.print("Get your anon key from: https://supabase.com/dashboard/project/zzdwykxtcxcahxtzojtw/settings/api")
        return

    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check if already loaded
    result = supabase.table("bible_verses").select("id", count="exact").limit(1).execute()
    if result.count and result.count > 0:
        console.print(f"[yellow]Database already contains {result.count} verses.[/yellow]")
        if not console.input("Reload? [y/N]: ").lower().startswith("y"):
            return
        console.print("[dim]Clearing existing verses...[/dim]")
        supabase.table("bible_verses").delete().neq("id", 0).execute()

    # Download and parse Bible
    bible_data = download_bible()
    verses = parse_bible(bible_data)
    console.print(f"[green]Parsed {len(verses)} verses[/green]")

    # Process in batches
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding and uploading...", total=len(verses))

        for i in range(0, len(verses), BATCH_SIZE):
            batch = verses[i:i + BATCH_SIZE]
            texts = [v["text"] for v in batch]

            # Create embeddings
            embeddings = create_embeddings(texts)

            # Add embeddings to records
            for verse, embedding in zip(batch, embeddings):
                verse["embedding"] = embedding

            # Insert batch
            supabase.table("bible_verses").insert(batch).execute()
            progress.update(task, advance=len(batch))

    console.print(f"[bold green]Loaded {len(verses)} verses into Supabase![/bold green]")


if __name__ == "__main__":
    main()
