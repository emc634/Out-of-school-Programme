from flask import session
import sqlite3
import os




#DB connection for user sign in and sign up
def get_db_connection(db_name):
    # Initialize database if it doesn't exist
    if not os.path.exists(db_name):
        conn = sqlite3.connect(db_name)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                can_id VARCHAR PRIMARY KEY,
                password TEXT NOT NULL,
                student_name TEXT NOT NULL,
                father_name TEXT,
                mother_name TEXT,
                dob TEXT,  -- SQLite doesn't have native date type
                gender TEXT,
                religion TEXT,
                category TEXT,
                aadhar TEXT UNIQUE,
                mobile TEXT,
                center TEXT,
                subcenter TEXT,
                trade TEXT,
                account_number TEXT,
                account_holder TEXT,
                ifsc TEXT,
                ojt TEXT,
                guest_lecture TEXT,
                industrial_visit TEXT,
                assessment TEXT
            )
        ''')
        conn.commit()
    else:
        conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


