"""Chat interface for FutureProof conversational agent.

Provides terminal-native chat UI using Rich for output and prompt-toolkit for input.
"""

from futureproof.chat.client import run_chat, run_chat_async
from futureproof.chat.ui import (
    display_error,
    display_insights,
    display_response,
    display_welcome,
)

__all__ = [
    "run_chat",
    "run_chat_async",
    "display_welcome",
    "display_response",
    "display_insights",
    "display_error",
]
