#!/usr/bin/env python3
"""Query Bible verses by mood, feeling, or topic."""

import os
import sys
from pathlib import Path

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from supabase import create_client

# Load .env file if present
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

console = Console()

# Supabase Phoenix project
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zzdwykxtcxcahxtzojtw.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def search_verses(query: str, limit: int = 5, threshold: float = 0.3) -> list[dict]:
    """Search for Bible verses matching the query."""
    if not SUPABASE_KEY:
        console.print("[red]Error: SUPABASE_KEY environment variable required[/red]")
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Create embedding for query
    response = ollama.embed(model="nomic-embed-text", input=query)
    query_embedding = response["embeddings"][0]

    # Search using the Supabase function
    result = supabase.rpc(
        "search_bible_verses",
        {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
        },
    ).execute()

    return result.data


def display_results(query: str, results: list[dict]):
    """Display search results nicely."""
    if not results:
        console.print(f"[yellow]No verses found matching '{query}'[/yellow]")
        console.print("[dim]Try a different phrase or lower the threshold[/dim]")
        return

    console.print(f"\n[bold]Verses for:[/bold] [italic]{query}[/italic]\n")

    for i, verse in enumerate(results, 1):
        similarity_pct = verse["similarity"] * 100
        color = "green" if similarity_pct > 50 else "yellow" if similarity_pct > 35 else "dim"

        panel = Panel(
            f"[white]{verse['text']}[/white]",
            title=f"[bold blue]{verse['reference']}[/bold blue]",
            subtitle=f"[{color}]{similarity_pct:.0f}% match[/{color}]",
            border_style="blue",
        )
        console.print(panel)


def interactive_mode():
    """Run in interactive mode."""
    console.print(Panel(
        "[bold]Bible Verse Search[/bold]\n\n"
        "Enter a mood, feeling, or topic to find matching verses.\n"
        "Examples: 'feeling anxious', 'need hope', 'grateful', 'overwhelmed'\n\n"
        "[dim]Type 'quit' or 'q' to exit[/dim]",
        border_style="green",
    ))

    while True:
        try:
            query = console.input("\n[bold green]>[/bold green] ").strip()
            if not query or query.lower() in ("quit", "q", "exit"):
                console.print("[dim]Goodbye![/dim]")
                break

            # Parse optional limit: "anxious -n 10"
            limit = 5
            if " -n " in query:
                parts = query.split(" -n ")
                query = parts[0]
                try:
                    limit = int(parts[1])
                except ValueError:
                    pass

            results = search_verses(query, limit=limit)
            display_results(query, results)

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Command line mode: bible "feeling anxious"
        query = " ".join(sys.argv[1:])
        results = search_verses(query)
        display_results(query, results)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
