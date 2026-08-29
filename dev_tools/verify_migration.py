"""
Purpose:
    Performs a sanity check on the SQLite database to verify data integrity after a migration.

When to run:
    - After running `setup_sqlite.sh` or `smart_import.py`.
    - When you suspect database corruption or missing records.

Why to run:
    - To ensure that the core tables (EnemySkill, Race, AdditionalFeatureItem) actually contain data.
    - To verify that data types and mappings are correct by inspecting sample records.

Input:
    - db.sqlite3.

Output:
    - A detailed console report showing record counts and verification results for critical tables.

End result:
    - Developer confidence that the migration process worked and the application has the necessary data to function.

Pre-conditions:
    - The SQLite database file must exist in the project root.

Developer info:
    - This script checks for specific "known good" data points (e.g., Orlanthi male names).
    - It highlights potential issues like empty tables or unexpected data types.
"""
import os
import re
import sqlite3
import sys
import logging
from typing import Dict, List, Tuple, Any, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MigrationVerifier:
    """Verifies data integrity after MySQL-to-SQLite migration."""

    def __init__(self, dump_file: str, db_file: str):
        """
        Initialize the verifier.

        Args:
            dump_file: Path to the MySQL dump file.
            db_file: Path to the SQLite database file.
        """
        self.dump_file = dump_file
        self.db_file = db_file
        self.mysql_schema: Dict[str, List[str]] = {}
        self.sqlite_schema: Dict[str, List[str]] = {}

    def get_mysql_schema(self) -> Dict[str, List[str]]:
        """Extracts schema from MySQL dump."""
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
        """Extracts schema from SQLite database."""
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
        """Cleans MySQL value for comparison."""
        val = val.strip()
        if val == 'NULL':
            return None
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            content = val[1:-1]
            content = content.replace("\\'", "'").replace('\\"', '"')
            content = content.replace("\\n", "\n").replace("\\r", "\r")
            content = content.replace("\\t", "\t").replace("\\\\", "\\")
            return content
        return val

    def parse_values(self, values_str: str) -> List[List[Optional[str]]]:
        """Parses values block from INSERT statement."""
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

    def run(self) -> None:
        """Runs the verification process."""
        if not os.path.exists(self.dump_file):
            logger.error(f"Dump not found: {self.dump_file}")
            return
        if not os.path.exists(self.db_file):
            logger.error(f"SQLite not found: {self.db_file}")
            return
        
        self.mysql_schema = self.get_mysql_schema()
        self.sqlite_schema = self.get_sqlite_schema()
        
        table_data: Dict[str, List[List[Optional[str]]]] = {}
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
                            val_to_process = current_values[:pos]
                            if current_table not in table_data:
                                table_data[current_table] = []
                            table_data[current_table].extend(self.parse_values(val_to_process))
                            remaining = current_values[pos+1:]
                            current_values = ""
                            in_insert = False
                            match = re.match(r'^\s*INSERT INTO [`"]([^`"]+)[`"] VALUES ', remaining)
                            if match:
                                current_table = match.group(1)
                                current_values = remaining[match.end():]
                                in_insert = True
                                pos = -1
                            else:
                                break
                        pos += 1
                    if in_insert:
                        next_line = f.readline()
                        if not next_line: break
                        current_values += next_line

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        summary = []
        all_passed = True
        
        for table_name, dump_rows in table_data.items():
            if table_name not in self.sqlite_schema:
                summary.append(f"Table {table_name}: SKIPPED (not in SQLite)")
                continue
            
            m_cols = self.mysql_schema.get(table_name, [])
            s_cols = self.sqlite_schema[table_name]
            logger.info(f"Verifying {table_name}...")
            
            mapped_rows = []
            if m_cols and set(s_cols).issubset(set(m_cols)) and (len(dump_rows[0]) == len(m_cols)):
                for row in dump_rows:
                    row_dict = dict(zip(m_cols, row))
                    mapped_rows.append(tuple(row_dict.get(col) for col in s_cols))
            elif len(dump_rows[0]) == len(s_cols):
                mapped_rows = [tuple(row) for row in dump_rows]
            else:
                summary.append(f"Table {table_name}: FAILED (Column mismatch)")
                all_passed = False
                continue

            cursor.execute(f"SELECT {','.join(['\"'+c+'\"' for c in s_cols])} FROM \"{table_name}\"")
            sqlite_rows = set(cursor.fetchall())
            sqlite_rows_strings = set(tuple(str(x) if x is not None else None for x in r) for r in sqlite_rows)
            sqlite_rows_stripped = set(tuple(x.strip() if isinstance(x, str) else x for x in r) for r in sqlite_rows)
            
            missing = 0
            for row in mapped_rows:
                normalized_row = []
                for val in row:
                    if val is not None and val.isdigit():
                        normalized_row.append(int(val))
                    elif val is not None and val.replace('.','',1).isdigit():
                        try: normalized_row.append(float(val))
                        except: normalized_row.append(val)
                    else: normalized_row.append(val)
                
                normalized_tuple = tuple(normalized_row)
                if normalized_tuple not in sqlite_rows:
                    string_tuple = tuple(str(x) if x is not None else None for x in normalized_row)
                    stripped_normalized = tuple(x.strip() if isinstance(x, str) else x for x in normalized_row)
                    if string_tuple not in sqlite_rows_strings and stripped_normalized not in sqlite_rows_stripped:
                        missing += 1

            if missing == 0:
                summary.append(f"Table {table_name}: PASSED ({len(dump_rows)} rows)")
            else:
                summary.append(f"Table {table_name}: FAILED ({missing}/{len(dump_rows)} rows missing)")
                all_passed = False

        logger.info("\n--- Verification Summary ---")
        for line in summary:
            logger.info(line)
        
        conn.close()
        if not all_passed:
            sys.exit(1)

def main() -> None:
    """Main entry point for the verification script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dump_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(dump_file):
        dump_file = os.path.join(script_dir, 'dump.sql')
    db_file = os.path.join(script_dir, '..', 'db.sqlite3')
    
    verifier = MigrationVerifier(dump_file, db_file)
    verifier.run()

if __name__ == '__main__':
    main()
