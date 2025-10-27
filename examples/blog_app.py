"""
Simple blog application for VISTA V-Loop testing
"""
import sqlite3
from typing import List, Optional

def get_recent_posts(limit: int = 10) -> List[dict]:
    """Fetch recent blog posts"""
    # This is test code - in real app, use proper error handling
    conn = sqlite3.connect("blog.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM posts ORDER BY created_at DESC LIMIT {limit}"
    cursor.execute(query)
    return [dict(row) for row in cursor.fetchall()]

def hello(name: str) -> str:
    return f'Hello {name}!'

if __name__ == "__main__":
    print(hello("VISTA"))
