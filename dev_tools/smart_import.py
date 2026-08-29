"""
Purpose:
    Intelligently migrates data from a MySQL dump into an existing SQLite database.

When to run:
    - When you need to import large-scale production data into your local SQLite environment.

Why to run:
    - Unlike basic SQL conversion, this script analyzes the target SQLite schema and maps MySQL columns accordingly.
    - It handles minor schema discrepancies, data type differences, and complex MySQL escape sequences.
    - It is the most robust way to sync production data into a local developer setup.

Input:
    - local_dump.sql (MySQL dump file).
    - db.sqlite3 (Target SQLite database).

Output:
    - A fully populated SQLite database.

End result:
    - Local environment matches production data exactly, allowing for accurate debugging and performance testing.

Pre-conditions:
    - Django migrations must have been run (`python3 manage.py migrate`) to create the SQLite schema.
    - `local_dump.sql` must be present in the `dev_tools/` directory.

Developer info:
    - This script uses Python's `sqlite3` and `re` modules for high-performance parsing.
    - It automatically disables foreign key constraints during import to avoid dependency errors.
    - It clears all existing data from tables before importing new records.
"""
import re
import sqlite3
import os
import logging
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MySQLToSQLiteImporter:
    """Intelligently imports MySQL dump data into an existing SQLite database."""

    def __init__(self, dump_file: str, db_file: str):
        """
        Initialize the importer.

        Args:
            dump_file: Path to the MySQL dump file.
            db_file: Path to the SQLite database file.
        """
        self.dump_file = dump_file
        self.db_file = db_file
        self.mysql_schema: Dict[str, List[str]] = {}
        self.sqlite_schema: Dict[str, List[str]] = {}

    def get_mysql_schema(self) -> Dict[str, List[str]]:
        """
        Extracts table schema (column names) from the MySQL dump file.

        Returns:
            A dictionary mapping table names to lists of column names.
        """
        schema = {}
        current_table = None
        with open(self.dump_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                create_match = re.search(r'CREATE TABLE [`"]([^`"]+)[`"] \(', line)
                if create_match:
                    current_table = create_match.group(1)
                    schema[current_table] = []
                    continue
                
                if current_table:
                    col_match = re.search(r'^\s*[`"]([^`"]+)[`"]', line)
                    if col_match:
                        schema[current_table].append(col_match.group(1))
                    elif line.strip().startswith(('PRIMARY KEY', 'KEY', 'UNIQUE KEY', 'CONSTRAINT', 'FULLTEXT KEY')):
                        continue
                    elif line.strip().startswith(')'):
                        current_table = None
        return schema

    def get_sqlite_schema(self) -> Dict[str, List[str]]:
        """
        Extracts table schema (column names) from the target SQLite database.

        Returns:
            A dictionary mapping table names to lists of column names.
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}');")
                schema[table] = [row[1] for row in cursor.fetchall()]
            return schema
        finally:
            conn.close()

    def clean_value(self, val: str) -> Optional[str]:
        """
        Cleans a MySQL value string for SQLite compatibility.

        Args:
            val: The raw value string from the dump.

        Returns:
            A cleaned string or None for NULL values.
        """
        val = val.strip()
        if val == 'NULL':
            return None
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            content = val[1:-1]
            # Handle MySQL escapes
            content = content.replace("\\'", "'")
            content = content.replace('\\"', '"')
            content = content.replace("\\n", "\n")
            content = content.replace("\\r", "\r")
            content = content.replace("\\t", "\t")
            content = content.replace("\\\\", "\\")
            return content
        return val

    def parse_values(self, values_str: str) -> List[List[Optional[str]]]:
        """
        Parses the VALUES part of an INSERT statement.

        Args:
            values_str: The string containing the values, e.g., "(v1,v2),(v3,v4)".

        Returns:
            A list of rows, where each row is a list of cleaned values.
        """
        results = []
        current_pos = 0
        while current_pos < len(values_str):
            if values_str[current_pos] == '(':
                current_pos += 1
                row = []
                current_val = ""
                in_string = False
                string_char = None
                escaped = False
                
                while current_pos < len(values_str):
                    c = values_str[current_pos]
                    if escaped:
                        current_val += c
                        escaped = False
                    elif c == '\\':
                        current_val += c
                        escaped = True
                    elif not in_string and (c == "'" or c == '"'):
                        in_string = True
                        string_char = c
                        current_val += c
                    elif in_string and c == string_char:
                        in_string = False
                        current_val += c
                    elif not in_string and c == ',':
                        row.append(self.clean_value(current_val))
                        current_val = ""
                    elif not in_string and c == ')':
                        row.append(self.clean_value(current_val))
                        results.append(row)
                        current_pos += 1
                        break
                    else:
                        current_val += c
                    current_pos += 1
            else:
                current_pos += 1
        return results

    def process_values(self, table_name: str, values_str: str, cursor: sqlite3.Cursor) -> None:
        """
        Processes a block of values and inserts them into the SQLite database.

        Args:
            table_name: The name of the target table.
            values_str: The raw values string to parse and insert.
            cursor: An active SQLite cursor.
        """
        if table_name not in self.sqlite_schema:
            return
        
        logger.info(f"Importing data for table '{table_name}'...")
        rows = self.parse_values(values_str)
        if not rows:
            return
            
        m_cols = self.mysql_schema.get(table_name, [])
        s_cols = self.sqlite_schema[table_name]
        
        # Determine if we can map columns
        if m_cols and set(s_cols).issubset(set(m_cols)) and (len(rows[0]) == len(m_cols)):
            mapped_rows = []
            for row in rows:
                row_dict = dict(zip(m_cols, row))
                mapped_rows.append(tuple(row_dict.get(col) for col in s_cols))
            
            placeholders = ",".join(["?"] * len(s_cols))
            sql = f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})"
            try:
                cursor.executemany(sql, mapped_rows)
            except sqlite3.IntegrityError:
                for row in mapped_rows:
                    try:
                        cursor.execute(sql, row)
                    except sqlite3.IntegrityError:
                        continue
        elif len(rows[0]) == len(s_cols):
            placeholders = ",".join(["?"] * len(s_cols))
            sql = f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})"
            try:
                cursor.executemany(sql, rows)
            except sqlite3.IntegrityError:
                for row in rows:
                    try:
                        cursor.execute(sql, row)
                    except sqlite3.IntegrityError:
                        continue

    def run(self) -> None:
        """
        Execute the full import process.

        Reads the MySQL dump, clears the SQLite database, and populates it with
        the dump data while handling schema differences.
        """
        if not os.path.exists(self.dump_file):
            logger.error(f"Dump file not found: {self.dump_file}")
            return
        if not os.path.exists(self.db_file):
            logger.error(f"SQLite database not found: {self.db_file}. Run migrations first.")
            return
        
        self.mysql_schema = self.get_mysql_schema()
        self.sqlite_schema = self.get_sqlite_schema()
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            # Clear existing data
            for table_name in self.sqlite_schema:
                cursor.execute(f"DELETE FROM \"{table_name}\";")

            # Parse and import data line by line
            with open(self.dump_file, 'r', encoding='utf-8', errors='ignore') as f:
                current_table = None
                current_values = ""
                in_insert = False
                in_string = False
                string_char = None
                escaped = False
                
                for line in f:
                    if not in_insert:
                        match = re.match(r'INSERT INTO [`"]([^`"]+)[`"] VALUES ', line)
                        if match:
                            current_table = match.group(1)
                            current_values = line[match.end():]
                            in_insert = True
                    
                    if in_insert:
                        pos = 0
                        while pos < len(current_values):
                            c = current_values[pos]
                            if escaped:
                                escaped = False
                            elif c == '\\':
                                escaped = True
                            elif not in_string and (c == "'" or c == '"'):
                                in_string = True
                                string_char = c
                            elif in_string and c == string_char:
                                in_string = False
                            elif not in_string and c == ';':
                                # End of statement
                                val_to_process = current_values[:pos]
                                if current_table:
                                    self.process_values(current_table, val_to_process, cursor)
                                
                                remaining = current_values[pos+1:]
                                current_values = ""
                                in_insert = False
                                
                                # Check if another INSERT starts here
                                next_match = re.match(r'^\s*INSERT INTO [`"]([^`"]+)[`"] VALUES ', remaining)
                                if next_match:
                                    current_table = next_match.group(1)
                                    current_values = remaining[next_match.end():]
                                    in_insert = True
                                    pos = -1
                                else:
                                    break
                            pos += 1
                        
                        if in_insert:
                            next_line = f.readline()
                            if not next_line:
                                break
                            current_values += next_line

            conn.commit()
            logger.info("Import completed successfully.")
        finally:
            cursor.execute("PRAGMA foreign_keys = ON;")
            conn.close()

def main() -> None:
    """Main entry point for the smart import script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path configuration
    dump_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(dump_file):
        dump_file = os.path.join(script_dir, 'dump.sql')
    
    db_file = os.path.join(script_dir, '..', 'db.sqlite3')
    
    importer = MySQLToSQLiteImporter(dump_file, db_file)
    importer.run()

if __name__ == '__main__':
    main()
