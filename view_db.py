import sqlite3

# Path to your .db file
db_path = "student_data.db"  # replace with your actual file

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show all tables
print("Tables in the database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

print("\n")

# Loop through tables and show their contents
for table_name in tables:
    print(f"--- Data from table: {table_name[0]} ---")
    try:
        cursor.execute(f"SELECT * FROM {table_name[0]}")
        rows = cursor.fetchall()

        # Fetch column names
        col_names = [desc[0] for desc in cursor.description]
        print(" | ".join(col_names))  # column headers
        print("-" * 50)

        for row in rows:
            print(" | ".join(str(cell) for cell in row))

        print("\n")
    except Exception as e:
        print(f"Error reading table {table_name[0]}: {e}")

# Close connection
conn.close()
