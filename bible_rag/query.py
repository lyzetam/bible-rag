#!/usr/bin/env python3
"""Query Bible verses by mood, feeling, or topic.

Usage:
    bible "feeling anxious"           # Semantic search (default)
    bible -e anxious                  # Search by emotion tag
    bible --emotion depression        # Search by emotion (expands to related tags)
    bible --emotions                  # List available emotion search terms
"""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

from bible_toolkit.core import BibleClient

console = Console()


def get_client() -> BibleClient:
    """Get the Bible client singleton."""
    if not hasattr(get_client, "_client"):
        get_client._client = BibleClient()
    return get_client._client


def search_verses(query: str, limit: int = 5, threshold: float = 0.3) -> list[dict]:
    """Semantic search for Bible verses matching the query."""
    try:
        client = get_client()
        return client.search(query, limit=limit, threshold=threshold)
    except Exception as e:
        if "404" in str(e) or "Connection" in str(e):
            console.print("[red]Error: Ollama server not available for semantic search.[/red]")
            console.print("[dim]Semantic search requires Ollama running at the configured URL.[/dim]")
            console.print("[dim]Try emotion search instead: bible -e <emotion>[/dim]")
            return []
        raise


def search_by_emotion(emotion: str, limit: int = 10) -> list[dict]:
    """Search for verses by emotion tag (with synonym expansion)."""
    client = get_client()
    return client.search_by_emotion(emotion, limit=limit)


def display_results(query: str, results: list[dict], is_emotion: bool = False):
    """Display search results nicely."""
    if not results:
        console.print(f"[yellow]No verses found matching '{query}'[/yellow]")
        if is_emotion:
            console.print("[dim]Try: bible --emotions to see available emotion terms[/dim]")
        else:
            console.print("[dim]Try a different phrase or lower the threshold[/dim]")
        return

    mode = "emotion" if is_emotion else "semantic"
    console.print(f"\n[bold]Verses for:[/bold] [italic]{query}[/italic] [dim]({mode} search)[/dim]\n")

    for verse in results:
        if is_emotion:
            # Emotion search results
            reference = verse["reference"]
            emotions = verse.get("emotions", [])
            confidence = verse.get("confidence", 0)
            confidence_pct = confidence * 100
            color = "green" if confidence_pct > 80 else "yellow" if confidence_pct > 60 else "dim"

            # Get the actual verse text
            client = get_client()
            verse_data = client.get_verse(reference)
            text = verse_data["text"] if verse_data else "[Verse not found]"

            emotion_tags = ", ".join(emotions[:4])
            if len(emotions) > 4:
                emotion_tags += f" +{len(emotions) - 4}"

            panel = Panel(
                f"[white]{text}[/white]\n\n[dim]Emotions: {emotion_tags}[/dim]",
                title=f"[bold blue]{reference}[/bold blue]",
                subtitle=f"[{color}]{confidence_pct:.0f}% confidence[/{color}]",
                border_style="blue",
            )
        else:
            # Semantic search results
            similarity_pct = verse["similarity"] * 100
            color = "green" if similarity_pct > 50 else "yellow" if similarity_pct > 35 else "dim"

            panel = Panel(
                f"[white]{verse['text']}[/white]",
                title=f"[bold blue]{verse['reference']}[/bold blue]",
                subtitle=f"[{color}]{similarity_pct:.0f}% match[/{color}]",
                border_style="blue",
            )
        console.print(panel)


def display_emotions():
    """Display available emotion search terms."""
    client = get_client()
    emotions = client.get_available_emotions()

    console.print("\n[bold]Available Emotion Search Terms[/bold]\n")
    console.print("[dim]These terms expand to related emotions in the database.[/dim]\n")

    # Group by category (rough grouping by first letter ranges)
    cols = Columns(emotions, column_first=True, padding=(0, 2))
    console.print(cols)

    console.print(f"\n[dim]Total: {len(emotions)} searchable terms[/dim]")
    console.print("\n[bold]Example:[/bold] bible -e depression")
    console.print("[dim]Expands to: sorrow, despair, sadness, grief, discouragement, anguish[/dim]\n")


def interactive_mode(use_emotion: bool = False):
    """Run in interactive mode."""
    mode = "emotion" if use_emotion else "semantic"
    examples = (
        "'anxious', 'depression', 'hopeful', 'lonely'"
        if use_emotion
        else "'feeling anxious', 'need hope', 'grateful', 'overwhelmed'"
    )

    console.print(Panel(
        f"[bold]Bible Verse Search[/bold] [dim]({mode} mode)[/dim]\n\n"
        f"Enter a mood, feeling, or topic to find matching verses.\n"
        f"Examples: {examples}\n\n"
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
            limit = 10 if use_emotion else 5
            if " -n " in query:
                parts = query.split(" -n ")
                query = parts[0]
                try:
                    limit = int(parts[1])
                except ValueError:
                    pass

            if use_emotion:
                results = search_by_emotion(query, limit=limit)
            else:
                results = search_verses(query, limit=limit)
            display_results(query, results, is_emotion=use_emotion)

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search Bible verses by mood, feeling, or topic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bible "feeling anxious"      Semantic search (finds contextually similar verses)
  bible -e anxious             Emotion search (finds verses tagged with anxiety/fear/worry)
  bible -e depression          Emotion search (expands to sorrow, despair, sadness, etc.)
  bible --emotions             List all available emotion search terms
        """,
    )
    parser.add_argument("query", nargs="*", help="Search query (mood, feeling, or topic)")
    parser.add_argument(
        "-e", "--emotion",
        action="store_true",
        help="Search by emotion tag instead of semantic similarity",
    )
    parser.add_argument(
        "--emotions",
        action="store_true",
        help="List available emotion search terms",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Number of results to return (default: 5 for semantic, 10 for emotion)",
    )

    args = parser.parse_args()

    # List available emotions
    if args.emotions:
        display_emotions()
        return

    # Determine limit
    default_limit = 10 if args.emotion else 5
    limit = args.limit if args.limit else default_limit

    if args.query:
        # Command line mode
        query = " ".join(args.query)
        if args.emotion:
            results = search_by_emotion(query, limit=limit)
        else:
            results = search_verses(query, limit=limit)
        display_results(query, results, is_emotion=args.emotion)
    else:
        # Interactive mode
        interactive_mode(use_emotion=args.emotion)


if __name__ == "__main__":
    main()
