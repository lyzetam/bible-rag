"""Agent tools for Bible search and retrieval."""

from langchain_core.tools import tool

from ..data.curated_verses import detect_emotions, get_curated_verses
from ..services.bible import BibleService


@tool
def search_bible_verses(query: str, limit: int = 5) -> str:
    """Search for Bible verses semantically matching a query about feelings, situations, or topics.

    Use this tool when you need to find verses that relate to what someone is
    experiencing or asking about. The search uses semantic similarity to find
    relevant passages.

    Args:
        query: A description of the feeling, situation, or topic (e.g., "feeling anxious about the future", "need strength to forgive")
        limit: Maximum number of verses to return (default: 5)

    Returns:
        Formatted string with matching verses and their similarity scores
    """
    service = BibleService()
    results = service.search_verses(query, limit=limit, threshold=0.25)

    if not results:
        return f"No verses found matching '{query}'. Try rephrasing or using different keywords."

    output = []
    for verse in results:
        similarity = verse["similarity"] * 100
        output.append(
            f"**{verse['reference']}** ({similarity:.0f}% match)\n{verse['text']}\n"
        )

    return "\n".join(output)


@tool
def search_curated_verses(emotion: str) -> str:
    """Look up curated verses for a specific emotion or feeling.

    Use this tool when you've identified a specific emotion (anxiety, fear, grief,
    loneliness, hopelessness, guilt, anger, gratitude, etc.) and want to find
    verses that have been specifically selected for that emotion.

    This is more targeted than semantic search - use it when you know the emotion.

    Args:
        emotion: The emotion to find verses for (e.g., "anxiety", "fear", "grief", "hopelessness")

    Returns:
        List of verse references for the emotion, or a message if no curated verses exist
    """
    verses = get_curated_verses(emotion)

    if not verses:
        detected = detect_emotions(emotion)
        if detected:
            all_verses = []
            for em in detected[:2]:  # Limit to 2 emotions
                all_verses.extend(get_curated_verses(em)[:5])
            if all_verses:
                return f"Curated verses for detected emotions ({', '.join(detected)}):\n" + "\n".join(
                    all_verses[:8]
                )

        return f"No curated verses found for '{emotion}'. Try using search_bible_verses for a semantic search instead."

    # Return just references - the agent can use get_verse_context or search to get full text
    return f"Curated verses for '{emotion}':\n" + "\n".join(verses[:8])


@tool
def get_verse_context(book: str, chapter: int, verse: int, context_size: int = 2) -> str:
    """Get surrounding verses for context around a specific verse.

    Use this when you want to show the broader context of a verse, or when a
    verse reference mentions a range (like Philippians 4:6-7).

    Args:
        book: The book name (e.g., "Philippians", "Psalms", "John")
        chapter: The chapter number
        verse: The verse number (will get verses around this)
        context_size: How many verses before and after to include (default: 2)

    Returns:
        The verse with its surrounding context
    """
    service = BibleService()
    verses = service.get_verse_context(book, chapter, verse, context_size)

    if not verses:
        return f"Could not find context for {book} {chapter}:{verse}"

    output = [f"**{book} {chapter}:{verses[0]['verse']}-{verses[-1]['verse']}**\n"]
    for v in verses:
        marker = ">>>" if v["verse"] == verse else "   "
        output.append(f"{marker} v{v['verse']}: {v['text']}")

    return "\n".join(output)


@tool
def get_verse_by_reference(reference: str) -> str:
    """Get a specific verse by its reference.

    Use this when you have an exact verse reference and need to retrieve its text.

    Args:
        reference: The verse reference (e.g., "John 3:16", "Philippians 4:6")

    Returns:
        The verse text or an error message if not found
    """
    service = BibleService()
    verse = service.get_verse_by_reference(reference)

    if not verse:
        return f"Could not find verse: {reference}"

    return f"**{verse['reference']}**\n{verse['text']}"


@tool
def get_cross_references(reference: str, limit: int = 5) -> str:
    """Get related verses that connect to a specific verse.

    Use this tool when you want to show how a verse connects to other parts
    of Scripture, or to provide additional supporting passages.

    Args:
        reference: The verse reference (e.g., "Philippians 4:6", "John 3:16")
        limit: Maximum number of cross-references to return (default: 5)

    Returns:
        List of related verse references with relevance scores
    """
    service = BibleService()
    results = service.get_cross_references(reference, limit=limit)

    if not results:
        return f"No cross-references found for {reference}"

    output = [f"**Verses connected to {reference}:**\n"]
    for xref in results:
        output.append(f"- {xref['to_reference']} (relevance: {xref['votes']})")

    return "\n".join(output)


def get_all_tools() -> list:
    """Get all available tools for the Bible agent."""
    return [
        search_bible_verses,
        search_curated_verses,
        get_verse_context,
        get_verse_by_reference,
        get_cross_references,
    ]
