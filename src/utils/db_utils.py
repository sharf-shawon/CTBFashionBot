def normalize_database_url(database_url: str) -> str:
    if not database_url:
        return database_url
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url
