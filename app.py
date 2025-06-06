from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'bhuvnn'

def get_db_connection():
    # Initialize database if it doesn't exist
    if not os.path.exists('user.db'):
        conn = sqlite3.connect('user.db')
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
        conn = sqlite3.connect('user.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template("front.html")


# Student Sign in 
@app.route("/student_signin", methods=["GET","POST"])
def student_signin():
    if request.method == "POST":
        email = request.form.get("login-email")
        password = request.form.get("login-password")
        
        if not email or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("student_signin"))
            
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user is None or not check_password_hash(user['password_hash'], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("student_signin"))
            
        flash("Login successful!", "success")
        return redirect(url_for("student_profile"))
    
    return render_template("student_signup.html")  # Should be a different template



# Student Sign up page
@app.route('/student_signup', methods=["GET","POST"])
def student_signup():
    if request.method == "POST":
        first_name = request.form.get("firstName")  
        last_name = request.form.get("lastName") 
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        confirmation = request.form.get("confirmPassword")
        
        if not all([first_name, last_name, email, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return redirect(url_for("student_signup"))
            
        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
            return redirect(url_for("student_signup"))
            
        password_hash = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, mobile, password_hash) VALUES (?, ?, ?, ?, ?)",
                (first_name, last_name, email, mobile, password_hash)
            )
            conn.commit()
            conn.close()
            
            flash("Account created successfully, Please Login", "success")
            return redirect(url_for("student_profile"))
            
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
            return redirect(url_for("student_signin"))
        except Exception as e:
            flash(f"An error occurred during registration: {str(e)}", "error")
            return redirect(url_for("student_signup"))
        finally:
            conn.close()
    
    return render_template('student_signup.html')

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/student_profile')
def student_profile():
    return render_template('student_profile.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")