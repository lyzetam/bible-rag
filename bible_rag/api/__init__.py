"""Bible RAG API module."""

import os
import sys
from pathlib import Path

import uvicorn

# Load .env file if present
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def serve():
    """Run the FastAPI server."""
    # Check for required env vars
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)

    if not os.getenv("SUPABASE_KEY"):
        print("Error: SUPABASE_KEY environment variable required")
        sys.exit(1)

    uvicorn.run(
        "bible_rag.api.app:app",
        host="0.0.0.0",
        port=8010,
        reload=False,
    )


__all__ = ["serve"]
