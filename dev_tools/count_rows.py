import sqlite3
import os

def count_rows():
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3')
    
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
        except Exception:
            # Skip tables that might be problematic (like internal sqlite tables)
            pass
    
    conn.close()
    
    # Sort by table name
    results.sort(key=lambda x: x[0])
    
    print(f"{'Table Name':<50} | {'Row Count':>10}")
    print("-" * 63)
    for table_name, count in results:
        print(f"{table_name:<50} | {count:>10}")

if __name__ == "__main__":
    count_rows()
