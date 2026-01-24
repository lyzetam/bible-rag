#!/usr/bin/env python3
"""Migrate Bible data from Phoenix to dedicated Bible project."""

from supabase import create_client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

# Source: Phoenix project
PHOENIX_URL = "https://zzdwykxtcxcahxtzojtw.supabase.co"
PHOENIX_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp6ZHd5a3h0Y3hjYWh4dHpvanR3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgwMTQxMDYsImV4cCI6MjA4MzU5MDEwNn0.tPWhQbzs3ZNBVMdz72BdU6GfKiRv_AeTUXlmu8b7Dlk"

# Target: Bible project
BIBLE_URL = "https://rehpmoxczibgkwcawelo.supabase.co"
BIBLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlaHBtb3hjemliZ2t3Y2F3ZWxvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyOTM3NTksImV4cCI6MjA4NDg2OTc1OX0.TW6ukZSPs0GqhwiuffIQU-acrdgTjJzToq8d1htgW_g"

BATCH_SIZE = 500


def migrate_table(source, target, table_name: str, has_embedding: bool = False):
    """Migrate a table from source to target."""
    console.print(f"\n[blue]Migrating {table_name}...[/blue]")

    # Get count
    result = source.table(table_name).select("*", count="exact").limit(1).execute()
    total = result.count or 0

    if total == 0:
        console.print(f"[yellow]No data in {table_name}[/yellow]")
        return

    console.print(f"[dim]Found {total} rows[/dim]")

    # Check if target already has data
    existing = target.table(table_name).select("id", count="exact").limit(1).execute()
    if existing.count and existing.count > 0:
        console.print(f"[yellow]Target already has {existing.count} rows. Skipping.[/yellow]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Copying {table_name}...", total=total)

        offset = 0
        while offset < total:
            # Fetch batch
            result = source.table(table_name).select("*").range(offset, offset + BATCH_SIZE - 1).execute()

            if not result.data:
                break

            # Remove id field to let target auto-generate
            rows = []
            for row in result.data:
                row_copy = {k: v for k, v in row.items() if k != "id"}
                rows.append(row_copy)

            # Insert batch
            if rows:
                target.table(table_name).insert(rows).execute()

            progress.update(task, advance=len(result.data))
            offset += BATCH_SIZE

    console.print(f"[green]Migrated {table_name}[/green]")


def main():
    console.print("[bold]Bible Data Migration[/bold]")
    console.print(f"From: Phoenix ({PHOENIX_URL})")
    console.print(f"To:   Bible ({BIBLE_URL})")

    source = create_client(PHOENIX_URL, PHOENIX_KEY)
    target = create_client(BIBLE_URL, BIBLE_KEY)

    # Tables to migrate (in order due to potential dependencies)
    tables = [
        ("bible_verses", True),           # ~31k rows, has embedding
        ("bible_cross_references", False), # ~344k rows
        ("bible_books", False),            # 66 rows (may be partial)
        ("bible_chapter_summaries", False),
        ("bible_verse_insights", False),
        ("bible_emotion_tags", False),
    ]

    for table_name, has_embedding in tables:
        try:
            migrate_table(source, target, table_name, has_embedding)
        except Exception as e:
            console.print(f"[red]Error migrating {table_name}: {e}[/red]")

    console.print("\n[bold green]Migration complete![/bold green]")


if __name__ == "__main__":
    main()
