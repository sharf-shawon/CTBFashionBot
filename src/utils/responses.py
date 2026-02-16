import random

# Affirmative/Success responses (when query succeeds)
AFFIRMATIVE_RESPONSES = [
    "Got it! Here's what I found:",
    "Sure thing! Based on the data:",
    "Absolutely! Here's the answer:",
    "Perfect! Here's what I found:",
    "Done! Here's the information:",
]

# Negative/Out-of-scope responses
# (when data not found or question irrelevant)
NEGATIVE_RESPONSES = [
    (
        "I can't help with that question. Either relevant information wasn't found "
        "or I'm not allowed to access it."
    ),
    "Sorry, I don't have access to that data or the question is outside my scope.",
    "I couldn't find relevant information for that question.",
    "That's not something I can help with right now.",
    "I don't have the data needed to answer that question.",
]

# Waiting/Processing responses (shown while working)
WAITING_RESPONSES = [
    "Working on it...",
    "Searching the database...",
    "Let me check that for you...",
    "Processing your question...",
    "One moment, looking that up...",
]

# Error/Refusal responses (when something goes wrong)
ERROR_RESPONSES = [
    "Sorry, I couldn't process that right now. Please try again.",
    "Something went wrong. Please try again later.",
    "I ran into an issue. Please try again.",
    "Let me try that again...",
    "Something didn't work out. Please try again.",
]

# Database unavailable responses
DB_UNAVAILABLE_RESPONSES = [
    "The database is unavailable right now. Please try again later.",
    "I can't reach the database at the moment. Please try again soon.",
    "Database is currently down. Please try again later.",
    "Connection to the database failed. Please try again.",
]

# Access denied responses
ACCESS_DENIED_RESPONSES = [
    "You don't have permission to perform that action.",
    "I can't help with that - you don't have access.",
    "That action is not allowed for you.",
    "You're not authorized to do that.",
]


def get_random_affirmative() -> str:
    return random.choice(AFFIRMATIVE_RESPONSES)


def get_random_negative() -> str:
    return random.choice(NEGATIVE_RESPONSES)


def get_random_waiting() -> str:
    return random.choice(WAITING_RESPONSES)


def get_random_error() -> str:
    return random.choice(ERROR_RESPONSES)


def get_random_db_unavailable() -> str:
    return random.choice(DB_UNAVAILABLE_RESPONSES)


def get_random_access_denied() -> str:
    return random.choice(ACCESS_DENIED_RESPONSES)
