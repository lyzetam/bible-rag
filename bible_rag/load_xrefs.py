#!/usr/bin/env python3
"""Load Bible cross-references into Supabase."""

import os
import re
from pathlib import Path

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

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zzdwykxtcxcahxtzojtw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

XREF_PATH = Path(__file__).parent.parent / "data" / "cross_references.txt"
BATCH_SIZE = 500

# Book abbreviation mapping (OpenBible format -> full name)
BOOK_MAP = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus", "Num": "Numbers",
    "Deut": "Deuteronomy", "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth",
    "1Sam": "1 Samuel", "2Sam": "2 Samuel", "1Kgs": "1 Kings", "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles", "2Chr": "2 Chronicles", "Ezra": "Ezra", "Neh": "Nehemiah",
    "Esth": "Esther", "Job": "Job", "Ps": "Psalms", "Prov": "Proverbs",
    "Eccl": "Ecclesiastes", "Song": "Song of Solomon", "Isa": "Isaiah",
    "Jer": "Jeremiah", "Lam": "Lamentations", "Ezek": "Ezekiel", "Dan": "Daniel",
    "Hos": "Hosea", "Joel": "Joel", "Amos": "Amos", "Obad": "Obadiah",
    "Jonah": "Jonah", "Mic": "Micah", "Nah": "Nahum", "Hab": "Habakkuk",
    "Zeph": "Zephaniah", "Hag": "Haggai", "Zech": "Zechariah", "Mal": "Malachi",
    "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke", "John": "John",
    "Acts": "Acts", "Rom": "Romans", "1Cor": "1 Corinthians", "2Cor": "2 Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Phil": "Philippians", "Col": "Colossians",
    "1Thess": "1 Thessalonians", "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy", "2Tim": "2 Timothy", "Titus": "Titus", "Phlm": "Philemon",
    "Heb": "Hebrews", "Jas": "James", "1Pet": "1 Peter", "2Pet": "2 Peter",
    "1John": "1 John", "2John": "2 John", "3John": "3 John", "Jude": "Jude",
    "Rev": "Revelation",
}


def convert_reference(ref: str) -> str:
    """Convert OpenBible reference format to standard format.

    Examples:
        Gen.1.1 -> Genesis 1:1
        Prov.8.22-Prov.8.30 -> Proverbs 8:22-30
        Ps.119.105 -> Psalms 119:105
    """
    # Handle ranges (e.g., Prov.8.22-Prov.8.30)
    if "-" in ref and ref.count(".") > 2:
        parts = ref.split("-")
        start = convert_reference(parts[0])
        end_ref = parts[1]
        # Extract just the verse number from end if same book/chapter
        end_match = re.match(r"(\w+)\.(\d+)\.(\d+)", end_ref)
        if end_match:
            end_verse = end_match.group(3)
            return f"{start}-{end_verse}"

    # Single verse: Gen.1.1
    match = re.match(r"(\d?\w+)\.(\d+)\.(\d+)", ref)
    if match:
        book_abbr, chapter, verse = match.groups()
        book = BOOK_MAP.get(book_abbr, book_abbr)
        return f"{book} {chapter}:{verse}"

    return ref  # Return as-is if can't parse


def parse_xrefs(path: Path) -> list[dict]:
    """Parse cross-references file."""
    xrefs = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("From"):
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                from_ref = convert_reference(parts[0])
                to_ref = convert_reference(parts[1])
                try:
                    votes = int(parts[2])
                except ValueError:
                    votes = 0

                xrefs.append({
                    "from_reference": from_ref,
                    "to_reference": to_ref,
                    "votes": votes,
                })

    return xrefs


def main():
    """Load cross-references into Supabase."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY environment variable required[/red]")
        return

    if not XREF_PATH.exists():
        console.print(f"[red]Error: Cross-references file not found at {XREF_PATH}[/red]")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check if already loaded
    result = supabase.table("bible_cross_references").select("id", count="exact").limit(1).execute()
    if result.count and result.count > 0:
        console.print(f"[yellow]Database already contains {result.count} cross-references.[/yellow]")
        if not console.input("Reload? [y/N]: ").lower().startswith("y"):
            return
        console.print("[dim]Clearing existing cross-references...[/dim]")
        supabase.table("bible_cross_references").delete().neq("id", 0).execute()

    # Parse file
    console.print("[blue]Parsing cross-references...[/blue]")
    xrefs = parse_xrefs(XREF_PATH)
    console.print(f"[green]Parsed {len(xrefs)} cross-references[/green]")

    # Load in batches
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading...", total=len(xrefs))

        for i in range(0, len(xrefs), BATCH_SIZE):
            batch = xrefs[i:i + BATCH_SIZE]
            supabase.table("bible_cross_references").insert(batch).execute()
            progress.update(task, advance=len(batch))

    console.print(f"[bold green]Loaded {len(xrefs)} cross-references![/bold green]")


if __name__ == "__main__":
    main()
