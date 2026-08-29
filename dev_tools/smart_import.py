
import re
import sqlite3
import os

def get_mysql_schema(dump_file):
    schema = {}
    current_table = None
    with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
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

def get_sqlite_schema(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}');")
        schema[table] = [row[1] for row in cursor.fetchall()]
    conn.close()
    return schema

def clean_value(val):
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

def parse_values(values_str):
    # This is a very simple parser for (v1, v2), (v3, v4)
    # It doesn't handle all edge cases but should work for most Django dumps
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
                    row.append(clean_value(current_val.strip()))
                    current_val = ""
                elif not in_string and c == ')':
                    row.append(clean_value(current_val.strip()))
                    results.append(row)
                    current_pos += 1
                    break
                else:
                    current_val += c
                current_pos += 1
        else:
            current_pos += 1
    return results

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Prefer local_dump.sql if it exists
    dump_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(dump_file):
        dump_file = os.path.join(script_dir, 'dump.sql')
    
    db_file = os.path.join(script_dir, '..', 'db.sqlite3')
    
    if not os.path.exists(dump_file):
        print(f"Error: {dump_file} not found.")
        return
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found. Please run migrations first.")
        return
    
    mysql_schema = get_mysql_schema(dump_file)
    sqlite_schema = get_sqlite_schema(db_file)
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    for table_name in sqlite_schema:
        cursor.execute(f"DELETE FROM \"{table_name}\";")

    # Use a simpler but more robust line-by-line approach
    with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
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
                    # Check for end of statement on the same line
                    # But we need to handle strings/escapes even here
            
            if in_insert:
                # We need to find the semicolon that is NOT in a string
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
                        # End of statement!
                        val_to_process = current_values[:pos]
                        process_values(current_table, val_to_process, mysql_schema, sqlite_schema, cursor)
                        
                        # Reset for next possible statement on same line
                        remaining = current_values[pos+1:]
                        current_values = ""
                        in_insert = False
                        
                        # Check if another INSERT starts here
                        match = re.match(r'^\s*INSERT INTO [`"]([^`"]+)[`"] VALUES ', remaining)
                        if match:
                            current_table = match.group(1)
                            current_values = remaining[match.end():]
                            in_insert = True
                            pos = -1 # Restart loop for new current_values
                        else:
                            # Skip to next line
                            break
                    pos += 1
                
                if in_insert:
                    # Statement continues on next line
                    next_line = f.readline()
                    if not next_line:
                        break
                    current_values += next_line

    conn.commit()
    conn.close()
    print("Done!")

def process_values(table_name, values_str, mysql_schema, sqlite_schema, cursor):
    if table_name not in sqlite_schema:
        return
    
    print(f"Importing block for {table_name}...")
    rows = parse_values(values_str)
    if not rows:
        return
        
    m_cols = mysql_schema.get(table_name, [])
    s_cols = sqlite_schema[table_name]
    
    if m_cols and set(s_cols).issubset(set(m_cols)) and (len(rows[0]) == len(m_cols)):
        mapped_rows = []
        for row in rows:
            row_dict = dict(zip(m_cols, row))
            mapped_rows.append(tuple(row_dict.get(col) for col in s_cols))
        
        placeholders = ",".join(["?"] * len(s_cols))
        try:
            cursor.executemany(f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})", mapped_rows)
        except sqlite3.IntegrityError:
            for row in mapped_rows:
                try:
                    cursor.execute(f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})", row)
                except sqlite3.IntegrityError:
                    pass
    elif len(rows[0]) == len(s_cols):
        placeholders = ",".join(["?"] * len(s_cols))
        try:
            cursor.executemany(f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})", rows)
        except sqlite3.IntegrityError:
            for row in rows:
                try:
                    cursor.execute(f"INSERT OR REPLACE INTO \"{table_name}\" VALUES ({placeholders})", row)
                except sqlite3.IntegrityError:
                    pass

if __name__ == '__main__':
    main()
