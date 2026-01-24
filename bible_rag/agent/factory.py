"""Agent factory for creating Bible support agents."""

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from .prompts import get_system_prompt
from .tools import get_all_tools

PersonaType = Literal["companion", "preacher"]


def get_bible_support_agent(
    persona: PersonaType = "companion",
    model: str = "claude-sonnet-4-20250514",
):
    """Create a Bible support agent with the specified persona.

    Args:
        persona: The agent persona ("companion" or "preacher")
        model: The Anthropic model to use

    Returns:
        A configured ReAct agent ready for conversation
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable required")

    llm = ChatAnthropic(model=model, max_tokens=1024)
    tools = get_all_tools()
    memory = MemorySaver()
    system_prompt = get_system_prompt(persona)

    agent = create_react_agent(
        llm,
        tools,
        checkpointer=memory,
        prompt=SystemMessage(content=system_prompt),
    )

    return agent


def run_agent(
    agent,
    message: str,
    thread_id: str = "default",
) -> str:
    """Run the agent with a message and return the response.

    Args:
        agent: The agent to run
        message: The user's message
        thread_id: Thread ID for conversation memory

    Returns:
        The agent's response text
    """
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    # Get the last AI message
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            # Handle string or list content
            if isinstance(msg.content, str):
                return msg.content
            elif isinstance(msg.content, list):
                # Extract text from content blocks
                text_parts = []
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                return "".join(text_parts)

    return "I'm not sure how to respond to that."
