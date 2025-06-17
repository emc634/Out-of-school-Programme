from flask import Flask, render_template, request, flash, redirect, url_for,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

from functions import get_db_connection

app = Flask(__name__)
app.secret_key = 'bhuvnn'


@app.route('/')
def index():
    return render_template("front.html")



# Student Sign up page
@app.route('/student_signup', methods=["GET","POST"])
def student_signup():
    if request.method == "POST":
        student_name = request.form.get("studentName")   
        father_name = request.form.get("fatherName")
        mother_name=request.form.get("motherName")
        can_id=request.form.get("canId")
        mobile = request.form.get("mobile")
        religion=request.form.get("religion")
        category=request.form.get("category")
        dob=request.form.get('dob')
        district=request.form.get("district")
        center=request.form.get('center')
        trade=request.form.get("trade")
        gender=request.form.get("gender")
        password = request.form.get("password")
        confirmation = request.form.get("confirmPassword")
        
        # Store in session only for this request cycle
        session['form_data']= {
            'student_name': student_name,
            'father_name': father_name,
            'mother_name': mother_name,
            'gender':gender,
            'mobile': mobile,
            'can_id':can_id,
            'religion':religion,
            'category':category,
            'dob':dob,
            'district':district,
            'trade':trade,
            'center':center,
        }
        
        if not all([student_name, father_name, mother_name, gender, mobile,
                    can_id, religion, category, dob, district, trade, center, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return redirect(url_for("student_signup"))
            
        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
            return redirect(url_for("student_signup"))
            
        password_hash = generate_password_hash(password)
        
        try:
            conn = get_db_connection("student_data.db")
            conn.execute(
                "INSERT INTO students (can_id, student_name, father_name, mother_name, mobile, religion, category, dob, district, center, trade, gender, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (can_id, student_name, father_name, mother_name, mobile, religion, category, dob, district, center, trade, gender, password_hash)
            )
            conn.commit()
            
            flash("Account created successfully", "success")
            return redirect(url_for("student_profile"))
            
        except sqlite3.IntegrityError as e:
            # Handle duplicate primary key (can_id) or NOT NULL violations
            if 'UNIQUE constraint failed: students.can_id' in str(e):
                flash("Candidate ID already exists. Please use a different ID.", "error")
            elif 'NOT NULL constraint failed' in str(e):
                flash("Some required fields are missing. Please fill all fields.", "error")
            else:
                flash("Data integrity error: " + str(e), "error")
            return redirect(url_for('student_signup'))

        except sqlite3.OperationalError as e:
            flash("Database operational error: " + str(e), "error")
            return redirect(url_for('student_signup'))

        except Exception as e:
            flash("An unexpected error occurred: " + str(e), "error")
            return redirect(url_for('student_signup'))
        finally:
            conn.close()
    
    # Clear any old form data when rendering the template for GET requests
    form_data = session.pop('form_data', {})
    return render_template('student_signup.html', form_data=form_data)


# Student data entry
@app.route('/student_profile', methods=["GET", "POST"])
def student_profile():
    form_data=session.get("form_data",{})
    
    if request.method == "POST":
        can_id = form_data.get('can_id')
        aadhar=request.form.get('aadhar')
        account_number=request.form.get('accountNumber')
        account_holder=request.form.get("accountHolder")
        ifsc=request.form.get('ifsc')
        ojt=request.form.get('ojt')
        guest_lecture=request.form.get('guestLecture')
        industrial_visit=request.form.get('industrialVisit')
        assessment=request.form.get('assessment')
        
        current_data={
            'aadhar':aadhar,
            'account_number':account_number,
            'account_holder':account_holder,
            'ifsc':ifsc,
            'ojt':ojt,
            'guest_lecture':guest_lecture,
            'industrial_visit':industrial_visit,
            'assessment':assessment
        }
        
        merged_data={**form_data, **current_data}
        session['form_data']=merged_data
        
        
        # Database operations
        conn = None
        try:
            conn = get_db_connection("student_data.db")
            
            student=conn.execute("SELECT * FROM students WHERE can_id = ?", (can_id,)).fetchone()
            if student is None:
                flash("Candidate ID does not exist", "error")
                return redirect(url_for('student_profile'))
            conn.execute(
                """UPDATE students SET aadhar=?, account_number=?, account_holder=?, ifsc=?,
                   ojt=?, guest_lecture=?, industrial_visit=?, assessment=? WHERE can_id=?""",
                (aadhar, account_number, account_holder, ifsc, ojt, guest_lecture, industrial_visit, assessment,can_id)
                )

            conn.commit()
            flash("Profile Completion Successful", "success")
            session['can_id']=form_data.can_id
            session.pop('form_data',None)
            return redirect(url_for('profile_display'))

        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "aadhar" in error_msg:
                flash("Aadhar number already registered", "error")
            elif "account_number" in error_msg:
                flash("Account number already exists", "error")
            elif "can_id" in error_msg:
                flash("Candidate ID does not exist", "error")
            else:
                flash(f"Database integrity error: {str(e)}", "error")
            return redirect(url_for('student_profile'))

        except sqlite3.OperationalError as e:
            flash(f"Database operational error: {str(e)}", "error")
            return redirect(url_for('student_profile'))

        except ValueError as e:
            # For example, if you parse or validate fields and detect bad data
            flash(f"Invalid input data: {str(e)}", "error")
            return redirect(url_for('student_profile'))

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('student_profile'))

        finally:
            if conn:
                conn.close()
    form_data=session.get('form_data',{})
    return render_template('student_profile.html', form_data=form_data)


@app.route("/reset_password")
def reset_password():
    return render_template("reset_password.html")


# Student Sign in 
@app.route("/student_signin", methods=["GET","POST"])
def student_signin():
    if request.method == "POST":
        session.pop('form_data', None)
        can_id = request.form.get("canId")
        password = request.form.get("password")
        
        # Validate form inputs
        if not can_id or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("student_signin"))
        
        conn = None
        try:
            # Connect to database
            conn = get_db_connection("student_data.db")
            user = conn.execute(
                'SELECT * FROM students WHERE can_id = ?', 
                (can_id,)
            ).fetchone()
            
            # Verify credentials
            if user is None or not check_password_hash(user['password'], password):
                flash("Invalid CAN ID or password", "error")  # Updated message
                return redirect(url_for("student_signin"))
            
            # Successful login
            session['can_id'] = can_id  # Store CAN ID in session
            
            flash("Login successful!", "success")
            return redirect(url_for("profile_display"))
        
        except sqlite3.Error as e:
            flash("Database error. Please try again.", "error")
            return redirect(url_for("student_signin"))
        
        finally:
            if conn:
                conn.close()  # Ensure connection always closes
        
    login_data=session.pop('can_id',{})
    return render_template("student_signin.html",login_data=login_data) 

@app.route("/profile_display")
def profile_display():
    can_id = session.get('can_id')
    if not can_id:
        return redirect(url_for('student_signin'))

    conn = get_db_connection('student_data.db')
    student=conn.execute('SELECT * FROM students WHERE can_id = ?', (can_id,)).fetchone()
    conn.close()
    return render_template("profile_display.html",student=student)



@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")