from flask import Flask
from functions import get_db_connection
import os

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello from Flask on Vercel!'

@app.route('/test-db')
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return f"Database connected! Current time: {row[0]}"
    except Exception as e:
        return f"DB connection failed: {str(e)}"
