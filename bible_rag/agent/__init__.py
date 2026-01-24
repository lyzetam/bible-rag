"""Bible RAG Agent module."""

import argparse
import os
import sys
import uuid
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .factory import PersonaType, get_bible_support_agent, run_agent

# Load .env file if present
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


console = Console()


def interactive_chat(persona: PersonaType = "companion"):
    """Run interactive chat with the Bible support agent."""
    console.print(
        Panel(
            f"[bold]Bible Support Agent[/bold] ({persona} mode)\n\n"
            "Share what's on your heart, and I'll search for relevant Scripture.\n"
            "This is a safe space to talk about whatever you're going through.\n\n"
            "[dim]Type 'quit' or 'q' to exit[/dim]",
            border_style="green",
        )
    )

    try:
        agent = get_bible_support_agent(persona=persona)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    thread_id = str(uuid.uuid4())

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
            if not user_input or user_input.lower() in ("quit", "q", "exit"):
                console.print("[dim]May you find peace. Goodbye![/dim]")
                break

            console.print()
            with console.status("[dim]Reflecting...[/dim]"):
                response = run_agent(agent, user_input, thread_id)

            # Render response as markdown
            console.print(Panel(Markdown(response), border_style="blue", title=""))

        except KeyboardInterrupt:
            console.print("\n[dim]May you find peace. Goodbye![/dim]")
            break


def main():
    """CLI entry point for bible-chat."""
    parser = argparse.ArgumentParser(
        description="Chat with the Bible support agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Personas:
  companion  Compassionate listener (default) - gentle, empathetic support
  preacher   Modern preacher - relatable, culturally-aware Scripture application

Examples:
  bible-chat                    # Start with companion persona
  bible-chat --persona preacher # Start with preacher persona
        """,
    )
    parser.add_argument(
        "--persona",
        "-p",
        choices=["companion", "preacher"],
        default="companion",
        help="Agent persona (default: companion)",
    )

    args = parser.parse_args()
    interactive_chat(persona=args.persona)


__all__ = ["get_bible_support_agent", "run_agent", "main", "PersonaType"]
