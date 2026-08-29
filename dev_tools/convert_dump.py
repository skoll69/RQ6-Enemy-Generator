"""
Purpose:
    Converts a MySQL dump file into a SQLite-compatible data-only SQL script.

When to run:
    - When you want to perform a manual data import into SQLite using the `sqlite3` CLI.
    - As an alternative to `smart_import.py` for troubleshooting or handling very large datasets.

Why to run:
    - MySQL and SQLite have different SQL dialects (e.g., quoting, escapes).
    - This script automates the tedious search-and-replace required to make a MySQL dump run on SQLite.

Input:
    - local_dump.sql (MySQL formatted dump).

Output:
    - local_data_only.sql (SQLite compatible script containing DELETE and INSERT statements).

End result:
    - A SQL script that can be executed directly: `sqlite3 db.sqlite3 < dev_tools/local_data_only.sql`.

Pre-conditions:
    - `local_dump.sql` must exist in the `dev_tools/` folder.

Developer info:
    - This script strips MySQL-specific headers, table creation statements, and locks.
    - It focuses exclusively on data (`INSERT` statements).
    - It assumes the SQLite schema has already been created by Django migrations.
"""
import os
import re
import sys
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MySQLToSQLiteConverter:
    """Converts a MySQL dump into a SQLite-compatible data-only SQL file."""

    def __init__(self, input_path: str, output_path: str):
        """
        Initialize the converter.

        Args:
            input_path: Path to the MySQL dump file.
            output_path: Path where the SQLite SQL file will be written.
        """
        self.input_path = input_path
        self.output_path = output_path

    def convert_line(self, line: str) -> Optional[str]:
        """
        Converts a single MySQL SQL line to SQLite format.

        Args:
            line: The SQL line to convert.

        Returns:
            The converted line, or None if the line should be skipped.
        """
        if not line or line.startswith(('--', '/*', 'LOCK TABLES', 'UNLOCK TABLES', 'DROP TABLE', 'SET ', '/*!')):
            return None
        
        # Replace backticks with double quotes
        line = line.replace('`', '"')
        
        # Only keep INSERT statements for now, as we'll use Django to create the schema
        if line.startswith('INSERT INTO'):
            # Convert MySQL escapes to SQLite
            line = line.replace("\\'", "''")
            line = line.replace('\\"', '"')
            return line
        
        return None

    def run(self) -> None:
        """
        Execute the conversion process.

        Reads the input MySQL dump, extracts table names, and writes a SQLite
        script that clears those tables and inserts the data.
        """
        if not os.path.exists(self.input_path):
            logger.error(f"Input file not found: {self.input_path}")
            return

        tables = set()
        # First pass to find all tables
        with open(self.input_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('INSERT INTO'):
                    match = re.search(r'INSERT INTO "([^"]+)"', line.replace('`', '"'))
                    if match:
                        tables.add(match.group(1))

        logger.info(f"Found {len(tables)} tables to process.")

        with open(self.input_path, 'r', encoding='utf-8', errors='ignore') as f:
            with open(self.output_path, 'w', encoding='utf-8') as out:
                out.write("PRAGMA foreign_keys=OFF;\n")
                out.write("BEGIN TRANSACTION;\n")
                
                # Clear all tables first
                for table in sorted(list(tables)):
                    out.write(f'DELETE FROM "{table}";\n')
                
                for line in f:
                    converted = self.convert_line(line)
                    if converted:
                        out.write(converted)
                
                out.write("COMMIT;\n")
                out.write("PRAGMA foreign_keys=ON;\n")
        
        logger.info(f"Successfully converted dump to {self.output_path}")

def main() -> None:
    """Main entry point for the dump conversion script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Prefer local_dump.sql if it exists
    input_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(input_file):
        input_file = os.path.join(script_dir, 'dump.sql')
        
    output_file = os.path.join(script_dir, 'local_data_only.sql')
    
    converter = MySQLToSQLiteConverter(input_file, output_file)
    converter.run()

if __name__ == '__main__':
    main()
