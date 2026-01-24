"""FastAPI application for Bible RAG agent."""

import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..agent.factory import get_bible_support_agent, run_agent
from ..services.bible import BibleService

app = FastAPI(
    title="Bible RAG API",
    description="Bible-based emotional support powered by semantic search and AI",
    version="0.1.0",
)

# Cache agents by persona to avoid recreation
_agents: dict = {}


def get_or_create_agent(persona: str):
    """Get cached agent or create new one."""
    if persona not in _agents:
        _agents[persona] = get_bible_support_agent(persona=persona)
    return _agents[persona]


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="The user's message", min_length=1)
    session_id: str | None = Field(
        None, description="Session ID for conversation continuity"
    )
    persona: Literal["companion", "preacher"] = Field(
        "companion", description="Agent persona to use"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str = Field(..., description="The agent's response")
    session_id: str = Field(..., description="Session ID for follow-up messages")


class VerseSearchRequest(BaseModel):
    """Request model for verse search."""

    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(5, description="Maximum results", ge=1, le=20)


class Verse(BaseModel):
    """Model for a Bible verse."""

    reference: str
    text: str
    similarity: float


class VerseSearchResponse(BaseModel):
    """Response model for verse search."""

    query: str
    verses: list[Verse]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "bible-rag"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the Bible support agent.

    Send a message and receive a thoughtful response with relevant Scripture.
    The agent maintains conversation context within a session.
    """
    try:
        agent = get_or_create_agent(request.persona)
        session_id = request.session_id or str(uuid.uuid4())

        response = run_agent(agent, request.message, session_id)

        return ChatResponse(
            response=response,
            session_id=session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/verses/search", response_model=VerseSearchResponse)
async def search_verses(query: str, limit: int = 5):
    """Search for Bible verses semantically.

    This is a direct search endpoint that bypasses the agent.
    Use this when you just want verse results without conversational context.
    """
    try:
        service = BibleService()
        results = service.search_verses(query, limit=limit)

        verses = [
            Verse(
                reference=v["reference"],
                text=v["text"],
                similarity=v["similarity"],
            )
            for v in results
        ]

        return VerseSearchResponse(query=query, verses=verses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/verses/{reference}")
async def get_verse(reference: str):
    """Get a specific verse by reference.

    Example: /verses/John 3:16
    """
    try:
        service = BibleService()
        verse = service.get_verse_by_reference(reference)

        if not verse:
            raise HTTPException(status_code=404, detail=f"Verse not found: {reference}")

        return {
            "reference": verse["reference"],
            "text": verse["text"],
            "book": verse["book"],
            "chapter": verse["chapter"],
            "verse": verse["verse"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
