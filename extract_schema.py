import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "database": "microinternDB",
    "user": "postgres",
    "password": "2810",
    "port": 5433
}

def get_schema():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    for table in tables:
        print(f"--- Table: {table} ---")
        cur.execute(f"SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = '{table}'")
        for col in cur.fetchall():
            print(col)
        print()
        
get_schema()
