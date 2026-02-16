"""Enrichment configuration for LLM and database."""

import os
from pathlib import Path

# Load .env file if present
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# Ollama on Mac Studio (128GB)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ms3.landryzetam.net:11434")

# Models available on Mac Studio (128GB)
# qwen3-vl:32b (21GB), gemma3:27b (17GB), gpt-oss:20b (14GB), glm-4.7-flash (19GB)
MODELS = {
    # Large model for complex generation (book summaries, verse insights)
    "large": "gemma3:27b",
    # Medium model for moderate tasks (chapter summaries)
    "medium": "gemma3:27b",
    # Small/fast model for classification (emotion tagging)
    "small": "gpt-oss:20b",
    # Embedding model (needs to be pulled: ollama pull nomic-embed-text)
    "embedding": "nomic-embed-text",
}

# Supabase - Bible project (set in .env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Batch processing
BATCH_SIZE = 10
MAX_RETRIES = 3
