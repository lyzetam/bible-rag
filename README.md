# Bible RAG

Semantic search for Bible verses by mood, feeling, or topic using pgvector.

## Setup

```bash
# Install dependencies
cd ~/dev/bible-rag
uv sync

# Set Supabase key (get from dashboard)
export SUPABASE_KEY="your_anon_key"

# Ensure Ollama has the embedding model
ollama pull nomic-embed-text

# Load Bible into Supabase (one-time, ~31k verses)
uv run bible-load
```

## Usage

```bash
# Interactive mode
uv run bible

# Direct query
uv run bible "feeling overwhelmed"
uv run bible "need courage"
uv run bible "thankful and grateful"
```

## Example Queries

- "feeling anxious and worried"
- "need strength and courage"
- "overwhelmed by life"
- "seeking peace"
- "feeling alone"
- "grateful and thankful"
- "need hope"
- "facing fear"
- "forgiveness"
- "love and patience"

## Architecture

- **Database**: Supabase (Phoenix project) with pgvector
- **Embeddings**: Ollama nomic-embed-text (768 dimensions)
- **Source**: KJV Bible (public domain)
- **Verses**: ~31,102 verses indexed
