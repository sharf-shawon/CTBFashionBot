"""Profanity detection and handling."""

import random
import re

# Common profanities and variations (case-insensitive)
PROFANITY_LIST = [
    "damn",
    "hell",
    "crap",
    "ass",
    "bastard",
    "bitch",
    "shit",
    "fuck",
    "piss",
    "dick",
    "cock",
    "pussy",
    "whore",
    "slut",
    "asshole",
    "douchebag",
    "twat",
    "wanker",
    "motherfucker",
    "bullshit",
    "horseshit",
    "jackass",
    "dipshit",
    "shithead",
    "fuckhead",
    "fuckwit",
    "asshat",
    "pissed",
    "cunts",
    "cunt",
    "nigger",
    "faggot",
]

PROFANITY_WARNINGS = [
    "We can't talk if you use words like that. Please continue a professional conversation.",
    "Let's keep this conversation professional. Please avoid using offensive language.",
    "I'd prefer if we kept things respectful. Please mind your language.",
    "I'm here to help, but let's keep it professional. No offensive language, please.",
    "That language isn't appropriate here. Let's have a professional discussion.",
    "I appreciate the question, but let's maintain a respectful tone, please.",
    "I'm happy to assist, but I need you to use professional language.",
    "Let's communicate respectfully. Offensive language isn't welcome here.",
]


def contains_profanity(text: str) -> bool:
    """
    Check if text contains any profanities.

    Args:
        text: The text to check

    Returns:
        True if profanity is detected, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()

    for word in PROFANITY_LIST:
        # Use word boundaries to avoid partial matches
        # This catches "damn" but not "damnit" as one word
        if re.search(r"\b" + re.escape(word) + r"\b", text_lower):
            return True

    return False


def get_random_profanity_warning() -> str:
    """Return a random profanity warning message."""
    return random.choice(PROFANITY_WARNINGS)
