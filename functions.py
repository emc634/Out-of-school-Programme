from flask import session
import sqlite3
import os




#DB connection for user sign in and sign up
def get_db_connection(db_name):
    # Initialize database if it doesn't exist
    if not os.path.exists(db_name):
        conn = sqlite3.connect(db_name)
        conn.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mobile TEXT,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()
    else:
        conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn


#DB connection for data entry for student

def get_student_data_db_connection(db_name):
    # Initialize database if it doesn't exist
    if not os.path.exists(db_name):
        conn = sqlite3.connect(db_name)
        conn.execute('''
                       CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                mother_name TEXT NOT NULL,
                dob TEXT NOT NULL,  -- SQLite doesn't have native date type
                gender TEXT NOT NULL,
                religion TEXT,
                category TEXT,
                aadhar TEXT UNIQUE NOT NULL,
                mobile TEXT NOT NULL,
                can_id TEXT UNIQUE NOT NULL,
                center TEXT NOT NULL,
                subcenter TEXT NOT NULL,
                trade TEXT NOT NULL,
                account_number TEXT NOT NULL,
                account_holder TEXT NOT NULL,
                ifsc TEXT NOT NULL,
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



#template for sessions
def get_template_data():
    """Helper function to get all template data from session"""
    return {
        'first_name': session.get("firstName", ""),
        'last_name': session.get("lastName", ""),
        'father_name': session.get("fatherName", ""),
        'mother_name': session.get("motherName", ""),
        'dob': session.get("dob", ""),
        'gender': session.get("gender", ""),
        'religion': session.get("religion", ""),
        'category': session.get("category", ""),
        'aadhar': session.get("aadhar", ""),
        'mobile': session.get("mobile", ""),
        'can_id': session.get("canID", ""),  # Note: canID from session
        'center': session.get("center", ""),
        'subcenter': session.get("subCenter", ""),
        'trade': session.get("trade", ""),
        'account_number': session.get("accountNumber", ""),
        'account_holder': session.get("accountHolder", ""),
        'ifsc': session.get("ifsc", ""),
        'ojt': session.get("ojt", ""),
        'guest_lecture': session.get("guestLecture", ""),
        'industrial_visit': session.get("industrialVisit", ""),
        'assessment': session.get("assessment", ""),
        'session': session  # Pass entire session for any additional template needs
    }
    
def clear_session_data():
    """Helper function to clear form data from session after successful submission"""
    fields_to_clear = [
        "firstName", "lastName", "fatherName", "motherName", "dob", "gender",
        "religion", "category", "aadhar", "mobile", "canID", "center", 
        "subCenter", "trade", "accountNumber", "accountHolder", "ifsc", 
        "ojt", "guestLecture", "industrialVisit", "assessment"
    ]
    
    for field in fields_to_clear:
        session.pop(field, None)