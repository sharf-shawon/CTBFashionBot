import random
import re

# Small talk detection patterns (case-insensitive, word boundaries)
GREETING_PATTERNS = [
    r"\b(hi|hello|hey|hiya|howdy|hallo|greetings|welcome)\b",
    r"\bwhat's?\s?up\b",
    r"\bhow\s?(are\s?you|do\s?you\s?do|ya\s?doing)\b",
    r"\bgood\s?(morning|afternoon|evening|day|night)\b",
    r"\bsalaam\b",
    r"\bnamaste\b",
]

FAREWELL_PATTERNS = [
    r"\b(bye|goodbye|farewell|see\s?ya|take\s?care|later|adios|ciao)\b",
    r"\bsee\s?you\b",
    r"\buntil\s?later\b",
    r"\bbye\s?bye\b",
]

SMALL_TALK_PATTERNS = [
    r"\b(thank|thanks|thankyou|appreciate)\b",
    r"\b(ok|okay|sure|yup|yeah|yes|nope|no)\b",
    r"\b(lol|haha|hehe|😂|🤣|😄|😊)\b",
    r"\b(cool|awesome|nice|great|sweet)\b",
    r"\b(what|who|where|when|why|how)\s*(\?|$)",
]

COMPILED_GREETINGS = [re.compile(pattern, re.IGNORECASE) for pattern in GREETING_PATTERNS]
COMPILED_FAREWELLS = [re.compile(pattern, re.IGNORECASE) for pattern in FAREWELL_PATTERNS]
COMPILED_SMALL_TALK = [re.compile(pattern, re.IGNORECASE) for pattern in SMALL_TALK_PATTERNS]

# Small talk responses
GREETING_RESPONSES = [
    "Hey there! 👋 What can I help you with?",
    "Hello! Ready to find some data? 📊",
    "Hi! What would you like to know?",
    "Howdy! Fire away with your question. 🚀",
    "Hey! What's on your mind?",
]

FAREWELL_RESPONSES = [
    "Catch you later! 👋",
    "Goodbye! Come back anytime! 👋",
    "See you! 📊",
    "Take care! 👍",
    "Goodbye! 👋",
]

SMALL_TALK_RESPONSES = [
    "Thanks for the chat! Got any data questions for me? 😊",
    "Appreciate it! Anything else I can help with? 📊",
    "Right on! What would you like to know? 🚀",
    "Cool! How can I assist you today? 📊",
    "You got it! What's your question? ❓",
]

CONFUSED_RESPONSES = [
    "That's interesting! But I'm really here to help with data questions. Got any? 📊",
    "I appreciate the chat, but I'm best with data-related questions. Whatcha need? 📊",
    "Haha, I like your style! But let me know if you have any data questions. 📊",
    "Fun thought! Though I'm mainly here to answer data questions. What do you need? 📊",
    "Ha! Let me know if you need any data insights. 📊",
]


def is_greeting(text: str) -> bool:
    """Check if text is a greeting."""
    return any(pattern.search(text) for pattern in COMPILED_GREETINGS)


def is_farewell(text: str) -> bool:
    """Check if text is a farewell."""
    return any(pattern.search(text) for pattern in COMPILED_FAREWELLS)


def is_small_talk(text: str) -> bool:
    """Check if text is small talk (greeting, farewell, or acknowledgement)."""
    if is_greeting(text) or is_farewell(text):
        return True
    return any(pattern.search(text) for pattern in COMPILED_SMALL_TALK)


def handle_greeting(text: str) -> str:
    """Return a response to a greeting."""
    if is_farewell(text):
        return random.choice(FAREWELL_RESPONSES)
    return random.choice(GREETING_RESPONSES)


def handle_small_talk(text: str) -> str:
    """Return a response to small talk."""
    if is_farewell(text):
        return random.choice(FAREWELL_RESPONSES)
    if is_greeting(text):
        return random.choice(GREETING_RESPONSES)
    return random.choice(SMALL_TALK_RESPONSES)


def handle_off_topic(text: str) -> str:
    """Return a response when user asks non-data question."""
    return random.choice(CONFUSED_RESPONSES)
