"""
Purpose:
    Provides a summary of the row counts for all tables in the SQLite database.

When to run:
    - Immediately after a database setup or migration.
    - Whenever you need to verify the scale of the current dataset.

Why to run:
    - To quickly verify if a migration was successful (e.g., confirming thousands of rows were imported).
    - To identify which data source (small fixture vs large dump) is currently active in the database.

Input:
    - db.sqlite3 (The local development database).

Output:
    - A formatted table in the console showing table names and their respective row counts.

End result:
    - Developer confirmation of the database's content and state.

Pre-conditions:
    - The SQLite database file must exist in the project root.

Developer info:
    - This script bypasses Django and uses the `sqlite3` library directly for speed.
    - It sorts tables alphabetically for easier reading.
"""
import sqlite3
import os
import logging
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DatabaseAnalyzer:
    """Analyzes SQLite database structure and content."""

    def __init__(self, db_path: str):
        """
        Initialize the analyzer.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path

    def get_table_counts(self) -> List[Tuple[str, int]]:
        """
        Retrieves the row count for every table in the database.

        Returns:
            A list of tuples containing (table_name, row_count).
        """
        if not os.path.exists(self.db_path):
            logger.error(f"Database not found: {self.db_path}")
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            results = []
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                    count = cursor.fetchone()[0]
                    results.append((table_name, count))
                except sqlite3.Error:
                    # Skip internal or locked tables
                    continue
            
            # Sort by table name
            results.sort(key=lambda x: x[0])
            return results
        finally:
            conn.close()

    def print_summary(self) -> None:
        """Prints a formatted table summary to the console."""
        results = self.get_table_counts()
        if not results:
            return

        print(f"\n{'Table Name':<50} | {'Row Count':>10}")
        print("-" * 63)
        for table_name, count in results:
            print(f"{table_name:<50} | {count:>10}")
        print("-" * 63)
        print(f"Total Tables: {len(results)}\n")

def main() -> None:
    """Main entry point for the row count script."""
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3')
    
    analyzer = DatabaseAnalyzer(db_path)
    analyzer.print_summary()

if __name__ == "__main__":
    main()
