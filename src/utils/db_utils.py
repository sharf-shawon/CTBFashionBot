def normalize_database_url(database_url: str) -> str:
    """Normalize database URLs for SQLAlchemy compatibility.

    Handles:
    - postgres:// -> postgresql+psycopg://
    - mysql:// -> mysql+pymysql://
    """
    if not database_url:
        return database_url
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+pymysql://", 1)
    return database_url
