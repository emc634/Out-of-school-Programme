import psycopg2
import os
from urllib.parse import urlparse
from datetime import date,datetime

def get_db_connection():
    conn = None
    cursor = None
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            url = urlparse(database_url)
            print(f"Connecting using DATABASE_URL to host: {url.hostname}")
            conn = psycopg2.connect(
                host=url.hostname,
                database=url.path[1:],
                user=url.username,
                password=url.password,
                port=url.port or 5432,
                sslmode='require'
            )
        else:
            # Your existing fallback code, add sslmode='require' here too
            pass
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        print("Database connection successful!")
        
        # your create table statements here...
        
        conn.commit()
        cursor.close()
        return conn
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"Error during DB connection/setup: {e}")
        raise



#Function to calculate the age 
def age_calculator(date_of_birth):
    dob=datetime.strptime(date_of_birth,'%Y-%m-%d').date()
    today=date.today()
    age=today.year-dob.year- ((today.month, today.day) < (dob.month, dob.day))
    return age

    