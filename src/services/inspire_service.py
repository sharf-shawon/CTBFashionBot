import random

from services.schema_service import SchemaService


class InspireService:
    """Generate inspiring sample questions based on database schema."""

    # Generic question templates
    TEMPLATES = [
        "How many {table}s are there?",
        "What's the total count of {table}?",
        "Show me the number of {table}s",
        "Count all {table}s",
        "How many {table}s were created today?",
        "What {column} values are in {table}?",
        "Show me distinct {column}s from {table}",
        "Average {column} in {table}?",
        "Top {column}s in {table}?",
        "Most recent {table}s?",
        "How many {table}s from this month?",
        "Compare {column} across {table}s",
        "Summarize {table} by {column}",
        "Which {table}s have the most {column}?",
        "Total of {column} in {table}?",
    ]

    def __init__(self, schema_service: SchemaService) -> None:
        self._schema_service = schema_service

    def generate_question(self) -> str | None:
        """Generate a sample question based on available schema.

        Returns None if schema is not available.
        """
        try:
            schema_info = self._schema_service.get_schema_info()
            if schema_info.connection_error or not schema_info.tables:
                return None

            tables = list(schema_info.tables.keys())
            if not tables:
                return None

            template = random.choice(self.TEMPLATES)
            selected_table = random.choice(tables)

            # If template has {column} placeholder, try to fill it
            if "{column}" in template:
                columns = schema_info.tables.get(selected_table, [])
                if not columns:
                    # Skip templates that require columns
                    return self.generate_question()
                selected_column = random.choice(columns)
                question = template.format(table=selected_table, column=selected_column)
            else:
                # Pluralize table name for readability
                pluralized = self._pluralize(selected_table)
                question = template.format(table=pluralized)

            return question.strip() + ("?" if not question.endswith("?") else "")
        except Exception:
            return None

    @staticmethod
    def _pluralize(word: str) -> str:
        """Simple pluralization - add 's' or 'es'."""
        if word.endswith(("s", "x", "z", "ch", "sh")):
            return word + "es"
        if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
            return word[:-1] + "ies"
        return word + "s"
