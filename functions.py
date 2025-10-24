import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse
from datetime import date, datetime, timezone, timedelta

def get_ist_time():
    """
    Get current time in Indian Standard Time (IST) without microseconds
    IST is UTC+5:30
    """
    ist_offset = timedelta(hours=5, minutes=30)
    ist_timezone = timezone(ist_offset)
    ist_time = datetime.now(ist_timezone)
    # Remove microseconds
    return ist_time.replace(microsecond=0)

def get_ist_date():
    """
    Get current date in Indian Standard Time (IST)
    """
    return get_ist_time().date()

def get_db_connection():
    """
    Create and return a PostgreSQL database connection.
    Creates the students table if it doesn't exist.
    """
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
                port=url.port or 5432
            )
        else:
            db_host = os.getenv('DB_HOST', 'localhost')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            db_port = os.getenv('DB_PORT', 5432)
            
            if not all([db_name, db_user, db_password]):
                missing_vars = []
                if not db_name: missing_vars.append('DB_NAME')
                if not db_user: missing_vars.append('DB_USER')
                if not db_password: missing_vars.append('DB_PASSWORD')
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            print(f"Connecting to PostgreSQL: {db_host}:{db_port}/{db_name} as {db_user}")
            
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        print("Database connection successful!")
        
        # Create all tables
        create_table_query = """
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            can_id VARCHAR(50) UNIQUE NOT NULL,
            student_name VARCHAR(100) NOT NULL,
            father_name VARCHAR(100) NOT NULL,
            mother_name VARCHAR(100) NOT NULL,
            batch_id VARCHAR(100) NOT NULL,
            trade VARCHAR(100) NOT NULL,
            mobile VARCHAR(15) NOT NULL,
            religion VARCHAR(50) NOT NULL,
            category VARCHAR(50) NOT NULL,
            dob DATE NOT NULL,
            district VARCHAR(100) NOT NULL,
            center VARCHAR(100) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            password TEXT NOT NULL
        );
        """
        
        create_student_training = """
        CREATE TABLE IF NOT EXISTS student_training(
            id SERIAL PRIMARY KEY,
            can_id VARCHAR(50) UNIQUE NOT NULL,
            single_counselling VARCHAR(50) DEFAULT 'Not Completed',
            group_counselling VARCHAR(50) DEFAULT 'Not Completed',
            ojt VARCHAR(50) DEFAULT 'Not Completed',
            guest_lecture VARCHAR(50) DEFAULT 'Not Completed',
            industrial_visit VARCHAR(50) DEFAULT 'Not Completed',
            assessment VARCHAR(50) DEFAULT 'Not Completed',
            assessment_date DATE,
            school_enrollment VARCHAR(50) DEFAULT NULL,
            udsi INT, 
            total_days INT DEFAULT 0,
            attendance INT DEFAULT 0,
            last_attendance_date DATE,
            other_trainings VARCHAR(50) DEFAULT NULL,
            FOREIGN KEY (can_id) REFERENCES students(can_id) ON DELETE CASCADE   
        )
        """
        
        create_bank_details = """
        CREATE TABLE IF NOT EXISTS bank_details(
            id SERIAL PRIMARY KEY,
            can_id VARCHAR(50) UNIQUE NOT NULL,
            aadhar VARCHAR(12) UNIQUE,
            account_number VARCHAR(20) UNIQUE,
            account_holder VARCHAR(100),
            ifsc VARCHAR(11),
            FOREIGN KEY (can_id) REFERENCES students(can_id) ON DELETE CASCADE 
        )
        """
        
        create_table_admin = """
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            email varchar(50) NOT NULL,
            password varchar(50) NOT NULL
        );
        """
        
        # UPDATED: IST timestamp without microseconds
        create_attendance_table = """
        CREATE TABLE IF NOT EXISTS daily_attendance (
            can_id VARCHAR(50) NOT NULL,
            attendance_date DATE NOT NULL,
            status VARCHAR(10) DEFAULT 'Absent' CHECK (status IN ('Present', 'Absent')),
            marked_at TIMESTAMP WITHOUT TIME ZONE,
            FOREIGN KEY (can_id) REFERENCES students(can_id) ON DELETE CASCADE,
            PRIMARY KEY (can_id, attendance_date)
        );
        """
        
        cursor.execute(create_table_query)
        print("Students table created/verified successfully!")
        
        cursor.execute(create_table_admin)
        print("Admin table created/verified successfully!")
        
        cursor.execute(create_student_training)
        print("Student training table created/verified successfully!")
        
        cursor.execute(create_bank_details)
        print("Bank details table created/verified successfully!")
        
        cursor.execute(create_attendance_table)
        print("Daily attendance table created/verified successfully!")
        
        # Create indexes
        index_queries = """
        CREATE INDEX IF NOT EXISTS idx_students_can_id ON students(can_id);
        CREATE INDEX IF NOT EXISTS idx_students_mobile ON students(mobile);
        CREATE INDEX IF NOT EXISTS idx_attendance_date ON daily_attendance(attendance_date);
        CREATE INDEX IF NOT EXISTS idx_attendance_can_id ON daily_attendance(can_id);
        CREATE INDEX IF NOT EXISTS idx_student_training_last_date ON student_training(last_attendance_date);
        """
        cursor.execute(index_queries)
        print("Indexes created/verified successfully!")
        
        conn.commit()
        cursor.close()
        
        return conn
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not connect to server" in error_msg:
            print(f"Connection failed: Cannot reach PostgreSQL server.")
        elif "authentication failed" in error_msg:
            print(f"Authentication failed: Check username and password.")
        elif "database" in error_msg and "does not exist" in error_msg:
            print(f"Database does not exist.")
        else:
            print(f"PostgreSQL Operational Error: {e}")
        raise
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
        
    finally:
        if cursor:
            cursor.close()

def age_calculator(date_of_birth):
    """Calculate age from date of birth"""
    dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
    today = get_ist_date()  # Use IST date
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age