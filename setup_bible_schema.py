#!/usr/bin/env python3
"""Set up schema on the Bible project using Supabase Management API."""

import httpx
from rich.console import Console

console = Console()

# Bible project
PROJECT_REF = "rehpmoxczibgkwcawelo"

# Management API (need service_role key or use dashboard)
# For now, print the SQL to run in Supabase SQL Editor

SCHEMA_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Bible verses with embeddings
CREATE TABLE IF NOT EXISTS bible_verses (
    id SERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    reference TEXT NOT NULL,
    text TEXT NOT NULL,
    translation TEXT DEFAULT 'KJV',
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cross references
CREATE TABLE IF NOT EXISTS bible_cross_references (
    id SERIAL PRIMARY KEY,
    from_reference TEXT NOT NULL,
    to_reference TEXT NOT NULL,
    votes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Book metadata
CREATE TABLE IF NOT EXISTS bible_books (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    abbreviation TEXT NOT NULL,
    testament TEXT NOT NULL CHECK (testament IN ('OT', 'NT')),
    position INTEGER NOT NULL,
    chapters INTEGER NOT NULL,
    verses INTEGER NOT NULL,
    author TEXT,
    date_written TEXT,
    audience TEXT,
    theme TEXT,
    summary TEXT,
    outline JSONB,
    key_verses JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    enriched_at TIMESTAMPTZ
);

-- Chapter summaries
CREATE TABLE IF NOT EXISTS bible_chapter_summaries (
    id SERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_count INTEGER NOT NULL,
    summary TEXT,
    themes JSONB,
    key_verses JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    enriched_at TIMESTAMPTZ,
    UNIQUE(book, chapter)
);

-- Verse insights
CREATE TABLE IF NOT EXISTS bible_verse_insights (
    id SERIAL PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    explanation TEXT,
    historical_context TEXT,
    application TEXT,
    cross_references JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    enriched_at TIMESTAMPTZ
);

-- Emotion tags
CREATE TABLE IF NOT EXISTS bible_emotion_tags (
    id SERIAL PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    emotions JSONB NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_verses_book ON bible_verses(book);
CREATE INDEX IF NOT EXISTS idx_verses_reference ON bible_verses(reference);
CREATE INDEX IF NOT EXISTS idx_verses_embedding ON bible_verses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_xref_from ON bible_cross_references(from_reference);
CREATE INDEX IF NOT EXISTS idx_xref_to ON bible_cross_references(to_reference);
CREATE INDEX IF NOT EXISTS idx_books_testament ON bible_books(testament);
CREATE INDEX IF NOT EXISTS idx_chapters_book ON bible_chapter_summaries(book);
CREATE INDEX IF NOT EXISTS idx_emotions_gin ON bible_emotion_tags USING GIN(emotions);

-- Search function for verses
CREATE OR REPLACE FUNCTION search_bible_verses(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id int,
    reference text,
    text text,
    book text,
    chapter int,
    verse int,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        bible_verses.id,
        bible_verses.reference,
        bible_verses.text,
        bible_verses.book,
        bible_verses.chapter,
        bible_verses.verse,
        1 - (bible_verses.embedding <=> query_embedding) AS similarity
    FROM bible_verses
    WHERE 1 - (bible_verses.embedding <=> query_embedding) > match_threshold
    ORDER BY bible_verses.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

def main():
    console.print("[bold]Bible Project Schema Setup[/bold]")
    console.print(f"\nProject: {PROJECT_REF}")
    console.print("\n[yellow]Run this SQL in Supabase SQL Editor:[/yellow]")
    console.print(f"https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
    console.print("\n" + "="*60 + "\n")
    print(SCHEMA_SQL)
    console.print("\n" + "="*60)
    console.print("\n[green]After running the SQL, run: uv run python migrate_to_bible_project.py[/green]")


if __name__ == "__main__":
    main()
