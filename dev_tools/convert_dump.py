
import os
import re
import sys

def convert_line(line):
    if not line or line.startswith(('--', '/*', 'LOCK TABLES', 'UNLOCK TABLES', 'DROP TABLE', 'SET ', '/*!')):
        return None
    
    # Replace backticks with double quotes
    line = line.replace('`', '"')
    
    # Only keep INSERT statements for now, as we'll use Django to create the schema
    if line.startswith('INSERT INTO'):
        # Convert MySQL escapes to SQLite
        line = line.replace("\\'", "''")
        line = line.replace('\\"', '"')
        # Some MySQL dumps use \0 for null? No, usually NULL.
        # Handle multiple values in one INSERT if needed (SQLite supports it)
        return line
    
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Prefer local_dump.sql if it exists
    input_file = os.path.join(script_dir, 'local_dump.sql')
    if not os.path.exists(input_file):
        input_file = os.path.join(script_dir, 'dump.sql')
        
    output_file = os.path.join(script_dir, 'local_data_only.sql')
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
    
    tables = set()
    # First pass to find all tables
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('INSERT INTO'):
                match = re.search(r'INSERT INTO "([^"]+)"', line.replace('`', '"'))
                if match:
                    tables.add(match.group(1))
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write("PRAGMA foreign_keys=OFF;\n")
            out.write("BEGIN TRANSACTION;\n")
            
            # Clear all tables first
            for table in sorted(list(tables)):
                out.write(f'DELETE FROM "{table}";\n')
            
            for line in f:
                converted = convert_line(line)
                if converted:
                    out.write(converted)
            
            out.write("COMMIT;\n")
            out.write("PRAGMA foreign_keys=ON;\n")

if __name__ == '__main__':
    main()
