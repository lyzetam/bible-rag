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

# Models available on Mac Studio (64GB)
# qwen3-vl:32b (20.9GB), gemma3:27b (17.4GB), gpt-oss:20b (13.8GB)
# deepseek-r1:14b (9GB), gemma3:4b (3.3GB), gemma3:1b (0.8GB)
MODELS = {
    # Large model for complex generation (book summaries, verse insights)
    "large": "gemma3:27b",
    # Medium model for moderate tasks (chapter summaries)
    "medium": "gemma3:27b",
    # Small/fast model for classification (emotion tagging)
    "small": "gemma3:4b",
    # Embedding model (needs to be pulled: ollama pull nomic-embed-text)
    "embedding": "nomic-embed-text",
}

# Supabase - Bible project
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rehpmoxczibgkwcawelo.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJlaHBtb3hjemliZ2t3Y2F3ZWxvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyOTM3NTksImV4cCI6MjA4NDg2OTc1OX0.TW6ukZSPs0GqhwiuffIQU-acrdgTjJzToq8d1htgW_g")

# Batch processing
BATCH_SIZE = 10
MAX_RETRIES = 3
