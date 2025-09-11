"""SQL Tool for executing database queries."""

import sqlite3
import os
from typing import Any


class SQLTool:
    """A simple SQLite tool for executing queries."""
    
    def __init__(self):
        """Initialize with database path."""
        
    
    def execute(self, query: str) -> str:
        """Execute a SQL query on Oracle and return results as a formatted string."""
        try:
            from django.db import connection
            # Only allow SELECT queries for safety
            if not query.strip().upper().startswith('SELECT'):
                return "Error: Only SELECT queries are allowed."
            with connection.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                if not rows:
                    return "No results found."
                # Format results as a table-like string
                output_lines = [" | ".join(columns)]
                output_lines.append("-" * len(output_lines[0]))
                for row in rows:
                    formatted_row = []
                    for i, value in enumerate(row):
                        if hasattr(value, 'read'):
                            formatted_row.append(str(value.read()))
                        else:
                            formatted_row.append(str(value))
                    output_lines.append(" | ".join(formatted_row))
                return "\n".join(output_lines)
        except Exception as e:
            return f"Error: {str(e)}"
