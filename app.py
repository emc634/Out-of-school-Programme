from flask import Flask, render_template, request, flash, redirect, url_for,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'bhuvnn'

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

@app.route('/')
def index():
    return render_template("front.html")



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
        
        #session names
        session['first_name'] = first_name
        session['last_name'] = last_name
        session["mobile"] = mobile
        session['email']=email
        
        if not all([first_name, last_name, email, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return render_template("student_signup.html",
                                   first_name=session.get("first_name",""),
                                   last_name=session.get("last_name",""),
                                   mobile=session.get("mobile",""),
                                   email=session.get("email","")
                                   )
            
        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
            return render_template("student_signup.html",
                                   first_name=session.get("first_name",""),
                                   last_name=session.get("last_name",""),
                                   mobile=session.get("mobile",""),
                                   email=session.get("email","")
                                   )
            
        password_hash = generate_password_hash(password)
        
        try:
            conn = get_db_connection("user.db")
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, mobile, password_hash) VALUES (?, ?, ?, ?, ?)",
                (first_name, last_name, email, mobile, password_hash)
            )
            conn.commit()
            
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
    
    return render_template("student_signup.html",email=session.get("email",""))  # Should be a different template


# Student data entry
@app.route('/student_profile',methods=["GET","POST"])
def student_profile():
    if request.method == "POST":
        firstname=request.form.get("firstName")
        lastname=request.form.get("lastName")
        fathername=request.form.get("fatherName")
        mothername=request.form.get("motherName")
        dob=request.form.get("dob")
        gender=request.form.get("gender")
        religion=request.form.get("religion")
        category=request.form.get("category")
        aadhar=request.form.get("aadhar")
        mobile=request.form.get("mobile")
        can_id=request.form.get("canID")
        center=request.form.get("center")
        subcenter=request.form.get("subCenter")
        trade=request.form.get("trade")
        acc_num=request.form.get("accountNumber")
        acc_holder=request.form.get("accountHolder")
        ifsc=request.form.get("ifsc")
        ojt=request.form.get("ojt")
        guest_lecture=request.form.get("guestLecture")
        industrial_visit=request.form.get("industrialVisit")
        assessment=request.form.get("assessment")

        # if not all([firstname, lastname, fathername, mothername, dob, 
        #             gender, religion, category, aadhar, mobile,
        #             can_id, center, subcenter, trade, acc_num, acc_holder,
        #             ifsc, ojt, guest_lecture, industrial_visit, assessment]):
        #     flash("Please fill in all required fields", "error")
        #     return redirect(url_for("student_profile"))
        try:
            conn=get_student_data_db_connection("student_data.db")
            conn = sqlite3.connect("student_data.db")
            cursor = conn.cursor()

            # Execute INSERT statement
            cursor.execute(
                """INSERT INTO students (
                    first_name, last_name, father_name, mother_name, dob, gender, religion, 
                    category, aadhar, mobile, can_id, center, subcenter, trade, account_number,
                    account_holder, ifsc, ojt, guest_lecture, industrial_visit, assessment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    firstname, lastname, fathername, mothername, dob, gender, religion,
                    category, aadhar, mobile, can_id, center, subcenter, trade, acc_num,
                    acc_holder, ifsc, ojt, guest_lecture, industrial_visit, assessment
                )
            )

            conn.commit()
            flash("Student data saved successfully!", "success")
            return redirect(url_for("student_profile"))

        except sqlite3.IntegrityError as e:
            # Handle unique constraint violations (e.g., duplicate aadhar/can_id)
            if "aadhar" in str(e).lower():
                flash("Aadhar number already registered", "error")
            elif "can_id" in str(e).lower():
                flash("Candidate ID already exists", "error")
            else:
                flash("Database integrity error: " + str(e), "error")
                return redirect(url_for("student_form_page"))  # Redirect back to form

        except Exception as e:
            flash(f"Error saving student data: {str(e)}", "error")
            return redirect(url_for("student_form_page"))

        finally:
            conn.close()


    return render_template('student_profile.html',
                           first_name=session.get("first_name",""),
                           last_name=session.get("last_name",""),
                           mobile=session.get("mobile","")
                           )
    
    

@app.route("/reset_password")
def reset_password():
    return render_template("reset_password.html")


@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")