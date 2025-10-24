from flask import Flask, render_template, request, flash, redirect, url_for, session,jsonify,send_file
import pandas as pd
import os
from datetime import datetime,date
import psycopg2
from dotenv import load_dotenv
from psycopg2 import extras
from datetime import datetime
import json
from psycopg2 import IntegrityError, OperationalError
from functools import wraps

from functions import get_db_connection,age_calculator
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')


course_days={
   "Agriculture":[50,"https://drive.google.com/file/d/1Ne5fPmmoC6W6JF92cIqe_uH40NXC5mCz/view?usp=drive_link"],
   "Beauty & Wellness": [70,"https://drive.google.com/file/d/1aI8JZfubWoA2cEeFl0BcyDQ7PZTHTtbC/view"],
   "Plumbing":[70,"https://drive.google.com/file/d/1tfs39122cJPT_JIU8Amj2F4LtYuazho0/view?usp=drive_link"],
   "Food Processing":[50,"https://drive.google.com/file/d/1RrPxtfiBjbs0ecYHK_5tVJbSUCkd3Dts/view?usp=drive_link"],
   "Automotive":[50,"https://drive.google.com/file/d/1wlYJdd5VgpxZnEhfw28D1AQ8RUZi98Cw/view?usp=drive_link"],
   "Electronics":[100,"https://drive.google.com/file/d/1VdM2kVZTTSZfSVSBkYRFYAqCZ_JanAkr/view?usp=drive_link"],
   "Tourism & Hospitality" :[66,"https://drive.google.com/file/d/1o2yYeaCteillbpOh8FdsPedl03Gg06Xt/view?usp=drive_link"],
   "Retail":[65,"https://drive.google.com/file/d/1m9frLws3Aepqm1iEgZB_JlHti97jTE19/view?usp=drive_link"]
}

def record_daily_attendance(can_id):
    """Record attendance in the daily_attendance table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO daily_attendance (can_id, attendance_date, status)
            VALUES (%s, %s, 'Present')
            ON CONFLICT (can_id, attendance_date) 
            DO UPDATE SET status = 'Present', marked_at = CURRENT_TIMESTAMP
        """, (can_id, date.today()))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error recording attendance: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'can_id' not in session:
            return redirect(url_for('front'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:  # You'll need to set this in admin_login
            return redirect(url_for('front'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def front():
    return render_template("front.html")



# Student Sign up page
@app.route('/student_signup', methods=["GET","POST"])
def student_signup():
    if request.method == "POST":
        student_name = request.form.get("studentName")   
        father_name = request.form.get("fatherName")
        mother_name=request.form.get("motherName")
        batch_id=request.form.get("batchId")
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
            'batch_id':batch_id,
            'mobile': mobile,
            'can_id':can_id,
            'religion':religion,
            'category':category,
            'dob':dob,
            'district':district,
            'trade':trade,
            'center':center
        }
        
        if not all([student_name, father_name,batch_id, mother_name, gender, mobile,
                    can_id, religion, category, dob, district, trade, center, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return redirect(url_for("student_signup"))
            
        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
            return redirect(url_for("student_signup"))
        
        if not mobile.isdigit() or len(mobile) != 10:
            flash("Mobile number must be exactly 10 digits", "error")
            return redirect(url_for("student_signup"))
            
        
        age=age_calculator(dob)
        if age<14:
            flash("Candidate must be atleast 14 to sign up", "error")
            return redirect(url_for("student_signup"))
        
        if age>18:
            flash("Candidate must be below 18 to sign up", "error")
            return redirect(url_for("student_signup"))
             
        password_hash = password
        
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                flash("Database connection failed. Please try again.", "error")
                return redirect(url_for("student_signup"))
            
            cursor = conn.cursor()
            
            # Start transaction explicitly
            conn.autocommit = False
            
            # FIX: Check for duplicate mobile BEFORE inserting
            cursor.execute("SELECT can_id FROM students WHERE mobile = %s", (mobile,))
            if cursor.fetchone():
                flash("Mobile number already registered", "error")
                return redirect(url_for("student_signup"))
            
            # FIX: Ensure column order matches value order
            cursor.execute("""
                INSERT INTO students 
                (can_id, student_name, batch_id, father_name, mother_name, 
                 mobile, trade, religion, category, dob, district, center, gender, password) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (can_id, student_name, batch_id, father_name, mother_name, 
                 mobile, trade, religion, category, dob, district, center, gender, password_hash)
            )
            
            cursor.execute(
                "INSERT INTO student_training (can_id, total_days) VALUES (%s, %s)",
                (can_id, course_days[trade][0])
            )
            
            conn.commit()
            
            # Set session AFTER successful database operations
            session['can_id'] = can_id
            
            flash("Account created successfully", "success")
            return redirect(url_for("student_profile"))
            
        except IntegrityError as e:
            if conn:
                conn.rollback()
            error_msg = str(e).lower()
            if 'can_id' in error_msg or 'duplicate key' in error_msg:
                flash("Candidate ID already exists. Please use a different ID.", "error")
            elif 'mobile' in error_msg:
                flash("Mobile number already registered", "error")
            else:
                flash(f"Data integrity error: {str(e)}", "error")
            return redirect(url_for('student_signup'))

        except OperationalError as e:
            if conn:
                conn.rollback()
            flash("Database operational error: " + str(e), "error")
            return redirect(url_for('student_signup'))

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Unexpected error: {str(e)}")
            flash("An unexpected error occurred: " + str(e), "error")
            return redirect(url_for('student_signup'))
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    # Clear any old form data when rendering the template for GET requests
    form_data = session.pop('form_data', {})
    return render_template('student_signup.html', form_data=form_data)


# Student data entry
@app.route('/student_profile', methods=["GET", "POST"])
@login_required
def student_profile():
    form_data=session.get("form_data",{})
    
    if request.method == "POST":
        can_id = form_data.get('can_id')
        aadhar=request.form.get('aadhar')
        account_number=request.form.get('accountNumber')
        account_holder=request.form.get("accountHolder")
        ifsc=request.form.get('ifsc')

        
        current_data={
            'aadhar':aadhar,
            'account_number':account_number,
            'account_holder':account_holder,
            'ifsc':ifsc
        }
        
        merged_data={**form_data, **current_data}
        session['form_data']=merged_data
        
        
        # Database operations
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("SELECT * FROM students WHERE can_id = %s", (can_id,))
            student = cursor.fetchone()
            if student is None:
                flash("Candidate ID does not exist", "error")
                return redirect(url_for('student_profile'))
            
            cursor.execute("INSERT INTO bank_details (can_id,aadhar,account_number,account_holder,ifsc) VALUES (%s,%s,%s,%s,%s)",
                (can_id, aadhar, account_number, account_holder, ifsc)
                )

            conn.commit()
            flash("Profile Completion Successful", "success")
            # FIXED: Changed from form_data.can_id to form_data.get('can_id')
            session['can_id']=form_data.get('can_id')
            session.pop('form_data',None)
            return redirect(url_for('profile_display'))

        except IntegrityError as e:
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

        except OperationalError as e:
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
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    form_data=session.get('form_data',{})
    return render_template('student_profile.html', form_data=form_data)



#Password Reset

@app.route("/reset_password", methods=["GET", "POST"])
@login_required
def reset_password():
    # Check if user is logged in
    can_id = session.get('can_id')
    if not can_id:
        flash("Please login to access this page", "error")
        return redirect(url_for('student_signin'))
    
    if request.method == "POST":
        current_password = request.form.get("currentPassword")
        new_password = request.form.get("newPassword")
        confirm_password = request.form.get("confirmPassword")
        
        # Validate form inputs
        if not all([current_password, new_password, confirm_password]):
            flash("Please fill in all password fields", "error")
            return redirect(url_for("reset_password"))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash("New passwords don't match. Please try again.", "error")
            return redirect(url_for("reset_password"))
        
        
        # Check if new password is different from current password
        if current_password == new_password:
            flash("New password must be different from current password", "error")
            return redirect(url_for("reset_password"))
        
        conn = None
        cursor = None
        try:
            # Connect to database and verify current password
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                'SELECT password FROM students WHERE can_id = %s', 
                (can_id,)
            )
            user = cursor.fetchone()
            
            if user is None:
                flash("User not found. Please login again.", "error")
                session.pop('can_id', None)
                return redirect(url_for("student_signin"))
            
            # Verify current password
            if user["password"]!=current_password:
                flash("Current password is incorrect", "error")
                return redirect(url_for("reset_password"))
            
            
            # Update password in database
            cursor.execute(
                'UPDATE students SET password = %s WHERE can_id = %s',
                (new_password, can_id)
            )
            conn.commit()
            
            flash("Password updated successfully!", "success")
            return redirect(url_for('profile_display'))
            
        except OperationalError as e:
            flash(f"Database operational error: {str(e)}", "error")
            return redirect(url_for('reset_password'))
            
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('reset_password'))
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # GET request - render the template
    return render_template("reset_password.html")


# Student Sign in 
@app.route("/student_signin", methods=["GET","POST"])
def student_signin():
    if request.method == "POST":
        session.pop('form_data', None)
        can_id = request.form.get("canId")
        password = request.form.get("password")
        
        if not can_id or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("student_signin"))
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT * FROM students WHERE can_id = %s', (can_id,))
            user = cursor.fetchone()
            
            if user is None or user['password'] != password:
                flash("Invalid CAN ID or password", "error")
                return redirect(url_for("student_signin"))
            
            # Set session for successful login
            session['can_id'] = can_id
            
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        
        except psycopg2.Error as e:
            flash("Database error. Please try again.", "error")
            return redirect(url_for("student_signin"))
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # FIX: Don't remove can_id from session when rendering template
    login_data = session.get('can_id', '')  # Use get() instead of pop()
    return render_template("student_signin.html", login_data=login_data)


#displaying profile
@app.route("/profile_display")
@login_required
def profile_display():
    can_id = session.get('can_id')
    if not can_id:
        return redirect(url_for('student_signin'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute('SELECT * FROM students WHERE can_id = %s', (can_id,))
    student = cursor.fetchone()
    
    cursor.execute('SELECT * FROM student_training WHERE can_id = %s', (can_id,))
    training=cursor.fetchone()
    cursor.execute('SELECT * FROM bank_details WHERE can_id = %s', (can_id,))
    bank = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("profile_display.html",student=student,bank=bank,training=training)


@app.route("/update_profile", methods=["GET", "POST"])
def update_profile():
    # Check if user is logged in
    can_id = session.get('can_id')
    if not can_id:
        flash("Please login to access this page", "error")
        return redirect(url_for('student_signin'))

    if request.method == "POST":
        # Get form data & strip/clean where needed
        student_name = request.form.get("studentName", "").strip()   
        father_name = request.form.get("fatherName", "").strip()
        mother_name = request.form.get("motherName", "").strip()
        dob = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        religion = request.form.get("religion", "").strip()
        category = request.form.get("category", "").strip()
        mobile = request.form.get("mobile", "").strip()
        single_counselling = request.form.get("single_counselling", "").strip()
        group_counselling = request.form.get("group_counselling", "").strip()
        ojt = request.form.get('ojt', "").strip()
        guest_lecture = request.form.get('guestLecture', "").strip()
        industrial_visit = request.form.get('industrialVisit', "").strip()
        other_trainings = request.form.get('other_trainings', "").strip()
        assessment = request.form.get('assessment', "").strip()
        school_name = request.form.get('schoolName', "").strip().upper()
        udsi = request.form.get('udsicode', "").strip()
        account_number = request.form.get('accountNumber', "").strip()
        account_holder = request.form.get('accountHolder', "").strip()
        ifsc = request.form.get('ifsc', "").strip()

        # Store form data in session
        session['update_form_data'] = {
            'studentName': student_name,
            'fatherName': father_name,
            'motherName': mother_name,
            'dob': dob,
            'gender': gender,
            'religion': religion,
            'category': category,
            'mobile': mobile,
            'ojt': ojt,
            'guest_lecture': guest_lecture,
            'industrial_visit': industrial_visit,
            'assessment': assessment,
            'group_counselling': group_counselling,
            'single_counselling': single_counselling,
            'school_enrollment': school_name,
            'udsi': udsi,
            'other_trainings': other_trainings,
            'ifsc': ifsc,
            'account_number': account_number,
            'account_holder': account_holder
        }

        # Validate mobile number format
        if mobile and (not mobile.isdigit() or len(mobile) != 10):
            flash("Please enter a valid 10-digit mobile number", "error")
            return redirect(url_for("update_profile"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Check if user exists
            cursor.execute('SELECT password FROM students WHERE can_id = %s', (can_id,))
            user = cursor.fetchone()
            if not user:
                flash("User not found. Please login again.", "error")
                session.pop('can_id', None)
                return redirect(url_for("student_signin"))

            # Check if mobile is already used by another user
            if mobile:
                cursor.execute(
                    'SELECT can_id FROM students WHERE mobile = %s AND can_id != %s',
                    (mobile, can_id)
                )
                if cursor.fetchone():
                    flash("Mobile number already registered with another account", "error")
                    return redirect(url_for("update_profile"))

            # Build dynamic updates
            update_fields_student, update_values_student = [], []
            update_fields_training, update_values_training = [], []
            update_fields_bank, update_values_bank = [], []

            # Students table
            for field, value, col in [
                (student_name, student_name, "student_name"),
                (father_name, father_name, "father_name"),
                (mother_name, mother_name, "mother_name"),
                (dob, dob, "dob"),
                (gender, gender, "gender"),
                (religion, religion, "religion"),
                (category, category, "category"),
                (mobile, mobile, "mobile")
            ]:
                if value:
                    update_fields_student.append(f"{col} = %s")
                    update_values_student.append(value)

            # Training table
            for field, col in [
                (single_counselling, "single_counselling"),
                (group_counselling, "group_counselling"),
                (other_trainings, "other_trainings"),
                (ojt, "ojt"),
                (guest_lecture, "guest_lecture"),
                (industrial_visit, "industrial_visit")
            ]:
                if field:
                    update_fields_training.append(f"{col} = %s")
                    update_values_training.append(field)

            if assessment:
                # Fetch attendance % from DB
                cursor.execute("SELECT attendance, total_days FROM student_training WHERE can_id = %s", (can_id,))
                att_row = cursor.fetchone()

                if att_row and att_row["total_days"] > 0:
                    attendance_percent = (att_row["attendance"] / att_row["total_days"]) * 100
                else:
                    attendance_percent = 0

                if attendance_percent >= 80:
                    update_fields_training.append("assessment = %s")
                    update_values_training.append(assessment)
                    update_fields_training.append("assessment_date = %s")
                    update_values_training.append(datetime.today().date())
                else:
                    flash("Assessment cannot be updated because your attendance is below 80%.", "error")
                    return redirect(url_for("update_profile"))

            if school_name:
                update_fields_training.append("school_enrollment = %s")
                update_values_training.append(school_name)
            if udsi:
                update_fields_training.append("udsi = %s")
                update_values_training.append(udsi)

            # Bank table
            if account_number:
                update_fields_bank.append("account_number = %s")
                update_values_bank.append(account_number)
            if ifsc:
                update_fields_bank.append("ifsc = %s")
                update_values_bank.append(ifsc)
            if account_holder:
                update_fields_bank.append("account_holder = %s")
                update_values_bank.append(account_holder)

            # Validate school_name & udsi dependency
            if "udsi = %s" in update_fields_training and "school_enrollment = %s" not in update_fields_training:
                flash('UDSI code cannot be filled without filling Enrolled School section', 'error')
                return redirect(url_for('update_profile'))
            if "school_enrollment = %s" in update_fields_training and "udsi = %s" not in update_fields_training:
                flash('Please make sure you fill the UDSI code of your Enrolled School too', 'error')
                return redirect(url_for('update_profile'))

            # If nothing to update
            if not (update_fields_student or update_fields_training or update_fields_bank):
                flash('No changes detected. Please modify at least one field.', 'info')
                return redirect(url_for('update_profile'))

            # Apply updates
            if update_fields_student:
                update_values_student.append(can_id)
                query = f"UPDATE students SET {', '.join(update_fields_student)} WHERE can_id = %s"
                cursor.execute(query, update_values_student)

            if update_fields_training:
                update_values_training.append(can_id)
                query = f"UPDATE student_training SET {', '.join(update_fields_training)} WHERE can_id = %s"
                cursor.execute(query, update_values_training)

            if update_fields_bank:
                update_values_bank.append(can_id)
                query = f"UPDATE bank_details SET {', '.join(update_fields_bank)} WHERE can_id = %s"
                cursor.execute(query, update_values_bank)

            # Single commit
            conn.commit()

            session.pop('update_form_data', None)
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile_display'))

        except IntegrityError as e:
            if "mobile" in str(e).lower():
                flash("Mobile number already registered", "error")
            else:
                flash(f"Database integrity error: {str(e)}", "error")
        except OperationalError as e:
            flash(f"Database operational error: {str(e)}", "error")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for('update_profile'))

    # GET request
    form_data = session.get('update_form_data', {})
    return render_template('update_profile.html', form_data=form_data)


@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    can_id = session.get('can_id')
    conn = None
    cursor = None
    student = None
    
    if not can_id:
        flash("Please log in to access the dashboard", "error")
        return redirect(url_for('student_signin'))
    
    if request.method == "POST":
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Check if already marked today
            cursor.execute("""
                SELECT last_attendance_date FROM student_training
                WHERE can_id = %s
            """, (can_id,))
            
            result = cursor.fetchone()
            
            if result and result['last_attendance_date'] == date.today():
                flash("Attendance already marked for today!", "info")
                return redirect(url_for('dashboard'))
            
            # Get current attendance and total days
            cursor.execute("""
                SELECT attendance, total_days FROM student_training
                WHERE can_id = %s
            """, (can_id,))
            
            attendance_data = cursor.fetchone()
            current_attendance = attendance_data['attendance'] or 0
            total_days = attendance_data['total_days'] or 0
            
            # Check if already completed
            if current_attendance >= total_days:
                flash("You have already completed all training days!", "info")
                return redirect(url_for('dashboard'))
            
            # Update attendance in student_training
            new_attendance = current_attendance + 1
            cursor.execute("""
                UPDATE student_training 
                SET attendance = %s, last_attendance_date = %s
                WHERE can_id = %s
            """, (new_attendance, date.today(), can_id))
            
            # FIX: Also record in daily_attendance table
            cursor.execute("""
                INSERT INTO daily_attendance (can_id, attendance_date, status)
                VALUES (%s, %s, 'Present')
                ON CONFLICT (can_id, attendance_date) DO NOTHING
            """, (can_id, date.today()))
            
            conn.commit()
            flash("Attendance marked successfully!", "success")
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Error marking attendance: {str(e)}", "error")
            return redirect(url_for('dashboard'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # GET request - Fetch student data
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT st.single_counselling, st.group_counselling, st.total_days, 
                st.attendance, st.last_attendance_date,
                st.ojt, st.industrial_visit, st.assessment, st.guest_lecture, 
                st.school_enrollment, st.other_trainings, s.trade
            FROM student_training st
            JOIN students s ON st.can_id = s.can_id
            WHERE st.can_id = %s
        ''', (can_id,))
        student = cursor.fetchone()

        if student:
            student['syllabus'] = course_days.get(student['trade'], ["", None])[1]
        
        if not student:
            flash("Student data not found", "warning")
            return render_template("dashboard.html", student=None, today_date=date.today())
    
    except Exception as e:
        flash("An unexpected error occurred while fetching data", "error")
        return render_template("dashboard.html", student=None, today_date=date.today())
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template("dashboard.html", student=student, today_date=date.today())



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get('password')
        
        # Validate inputs
        if not email or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("admin_login"))
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('SELECT * FROM admins WHERE email = %s', (email,))
            admin = cursor.fetchone()
            
            if admin is None or admin["password"] != password:
                flash("Invalid email or password", "error")
                return redirect(url_for('admin_login'))
            
            # FIX: Set admin_id in session for @admin_required decorator
            session['admin_id'] = admin['id']  # or admin['email'] depending on your admin table structure
            
            flash("Login Successful", "success")
            return redirect(url_for('admin_dashboard'))
        
        except psycopg2.Error as e:
            print("Login error:", str(e))
            flash("Database error. Please try again.", "error")
            return redirect(url_for('admin_login'))
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    return render_template('admin_login.html')


@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    # Current filters
    current_filters = {key: request.args.get(key) for key in [
        'trade', 'gender', 'district', 'center', 'ojt_status',
        'school', 'single_counselling', 'group_counselling',
        'assessment', 'industrial_visit', 'other_trainings'
    ]}

    default_counts = {
        'total_students': 0,
        'single_completed': 0,
        'group_completed': 0,
        'ojt_completed': 0,
        'guest_lecture_completed': 0,
        'industrial_visit_completed': 0,
        'assessment_completed': 0,
        'school_enrollment_count': 0,
        'other_training_completed': 0
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        # Base query
        training_query = """
            SELECT 
                COUNT(*) AS total_students,
                SUM(CASE WHEN st.single_counselling = 'Completed' THEN 1 ELSE 0 END) AS single_completed,
                SUM(CASE WHEN st.group_counselling = 'Completed' THEN 1 ELSE 0 END) AS group_completed,
                SUM(CASE WHEN st.ojt = 'Completed' THEN 1 ELSE 0 END) AS ojt_completed,
                SUM(CASE WHEN st.guest_lecture = 'Completed' THEN 1 ELSE 0 END) AS guest_lecture_completed,
                SUM(CASE WHEN st.industrial_visit = 'Completed' THEN 1 ELSE 0 END) AS industrial_visit_completed,
                SUM(CASE WHEN st.assessment = 'Completed' THEN 1 ELSE 0 END) AS assessment_completed,
                SUM(CASE WHEN st.school_enrollment IS NOT NULL AND st.school_enrollment <> '' THEN 1 ELSE 0 END) AS school_enrollment_count,
                SUM(CASE WHEN st.other_trainings IS NOT NULL AND st.other_trainings <> 'Not Completed' THEN 1 ELSE 0 END) AS other_training_completed
            FROM students s
            LEFT JOIN student_training st ON s.can_id = st.can_id
            WHERE 1=1
        """
        params = []

        # Mapping filters to query conditions
        filter_map = {
            'trade': "LOWER(TRIM(s.trade)) = LOWER(%s)",
            'gender': "LOWER(TRIM(s.gender)) = LOWER(%s)",
            'district': "LOWER(TRIM(s.district)) = LOWER(%s)",
            'center': "LOWER(TRIM(s.center)) = LOWER(%s)",
            'ojt_status': "LOWER(TRIM(st.ojt)) = LOWER(%s)",
            'single_counselling': "LOWER(TRIM(st.single_counselling)) = LOWER(%s)",
            'group_counselling': "LOWER(TRIM(st.group_counselling)) = LOWER(%s)",
            'assessment': "LOWER(TRIM(st.assessment)) = LOWER(%s)",
            'industrial_visit': "LOWER(TRIM(st.industrial_visit)) = LOWER(%s)",
        }

        for key, condition in filter_map.items():
            value = current_filters.get(key)
            if value:
                training_query += f" AND {condition}"
                params.append(value.strip())

        # Special handling filters
        if current_filters.get('school'):
            if current_filters['school'] == "Enrolled":
                training_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
            elif current_filters['school'] == "Not Enrolled":
                training_query += " AND (st.school_enrollment IS NULL OR TRIM(st.school_enrollment) = '')"

        if current_filters.get('other_trainings'):
            if current_filters['other_trainings'] == "Not Completed":
                training_query += " AND (st.other_trainings IS NULL OR LOWER(TRIM(st.other_trainings)) = 'not completed')"
            else:
                training_query += " AND LOWER(TRIM(st.other_trainings)) = LOWER(%s)"
                params.append(current_filters['other_trainings'].strip())

        cursor.execute(training_query, params)
        training_counts = cursor.fetchone() or default_counts

        # Today's attendance count - FIXED: Using student_training table
        cursor.execute(
            "SELECT COUNT(*) FROM student_training WHERE last_attendance_date = %s",
            (date.today(),)
        )
        todays_attendance_count = cursor.fetchone()[0] or 0

        # Total students (fallback to training_counts if missing)
        total_records = training_counts.get('total_students', 0)

        return render_template(
            'admin_dashboard.html',
            training_counts=training_counts,
            todays_attendance_count=todays_attendance_count,
            current_filters=current_filters,
            total_records=total_records
        )

    except Exception as e:
        print("Dashboard error:", e)
        flash("An error occurred while loading dashboard", "error")
        return render_template(
            "admin_dashboard.html",
            training_counts=default_counts,
            todays_attendance_count=0,
            current_filters=current_filters,
            total_records=0
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/admin_dashboard/modal_data')
def modal_data():
    training_type = request.args.get('type')
    district = request.args.get('district', '').strip()
    center = request.args.get('center', '').strip()
    gender = request.args.get('gender', '').strip()
    trade = request.args.get('trade', '').strip()
    date_filter = request.args.get('date', '').strip()  # NEW: Get date parameter
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        base_query = """
            SELECT 
                s.*, 
                st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                st.total_days, st.attendance, st.other_trainings, st.udsi,
                st.last_attendance_date,
                bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
            FROM students s
            LEFT JOIN student_training st ON s.can_id = st.can_id
            LEFT JOIN bank_details bd ON s.can_id = bd.can_id
            WHERE 1=1
        """
        
        params = []
        
        # Add training type condition
        if training_type and training_type != 'total':
            if training_type == 'school':
                base_query += " AND st.school_enrollment IS NOT NULL AND st.school_enrollment <> ''"
            elif training_type == 'other_trainings':
                base_query += " AND st.other_trainings <> 'Not Completed'"
            elif training_type == 'todays_attendance':
                # UPDATED: Use date filter if provided, otherwise use today
                if date_filter:
                    base_query += " AND st.last_attendance_date = %s"
                    params.append(date_filter)
                else:
                    base_query += " AND st.last_attendance_date = %s"
                    params.append(date.today())
            else:
                base_query += f" AND st.{training_type} = %s"
                params.append('Completed')
        
        # Add additional filters
        if district:
            base_query += " AND LOWER(s.district) = LOWER(%s)"
            params.append(district)
            
        if center:
            base_query += " AND LOWER(s.center) = LOWER(%s)"
            params.append(center)
            
        if gender:
            base_query += " AND s.gender = %s"
            params.append(gender)
            
        if trade:
            base_query += " AND s.trade = %s"
            params.append(trade)
        
        # Execute main query for student data
        cursor.execute(base_query, params)
        students = cursor.fetchall()
        
        # Calculate gender statistics
        total_count = len(students)
        male_count = sum(1 for student in students if student.get('gender', '').lower() == 'male')
        female_count = sum(1 for student in students if student.get('gender', '').lower() == 'female')
        other_count = total_count - male_count - female_count
        
        # Calculate percentages
        male_percentage = (male_count / total_count * 100) if total_count > 0 else 0
        female_percentage = (female_count / total_count * 100) if total_count > 0 else 0
        other_percentage = (other_count / total_count * 100) if total_count > 0 else 0
        
        # Convert to list of dicts for JSON serialization and format dates
        result = []
        for student in students:
            student_dict = dict(student)
            if student_dict.get('dob'):
                student_dict['dob'] = student_dict['dob'].strftime('%d-%m-%Y')
            if student_dict.get('assessment_date'):
                student_dict['assessment_date'] = student_dict['assessment_date'].strftime('%d-%m-%Y')
            if student_dict.get('last_attendance_date'):
                student_dict['last_attendance_date'] = student_dict['last_attendance_date'].strftime('%d-%m-%Y')
            result.append(student_dict)
        
        return jsonify({
            'students': result,
            'gender_stats': {
                'total': total_count,
                'male': {'count': male_count, 'percentage': round(male_percentage, 1)},
                'female': {'count': female_count, 'percentage': round(female_percentage, 1)},
                'other': {'count': other_count, 'percentage': round(other_percentage, 1)}
            }
        })
        
    except Exception as e:
        print("Modal data error:", str(e))
        return jsonify({
            'students': [],
            'gender_stats': {
                'total': 0,
                'male': {'count': 0, 'percentage': 0},
                'female': {'count': 0, 'percentage': 0},
                'other': {'count': 0, 'percentage': 0}
            }
        })
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/export_filtered_data')
def export_filtered_data():
    # Get all filter parameters from request
    filters = {
        'type': request.args.get('type', 'total'),
        'district': request.args.get('district', ''),
        'center': request.args.get('center', ''),
        'gender': request.args.get('gender', ''),
        'trade': request.args.get('trade', '')
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        base_query = """
            SELECT 
                s.can_id, s.student_name, s.father_name, s.mother_name, s.batch_id,
                s.mobile, s.religion, s.category, s.dob, s.district, s.center, s.gender,
                s.trade, st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture,
                st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment,
                st.total_days, st.attendance, st.other_trainings,
                bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
            FROM students s
            LEFT JOIN student_training st ON s.can_id = st.can_id
            LEFT JOIN bank_details bd ON s.can_id = bd.can_id
            WHERE 1=1
        """
        
        params = []
        
        # Add training type condition
        if filters['type'] != 'total':
            if filters['type'] == 'school':
                base_query += " AND st.school_enrollment IS NOT NULL AND st.school_enrollment <> ''"
            elif filters['type'] == 'other_trainings':
                base_query += " AND st.other_trainings <> 'Not Completed'"
            else:
                base_query += f" AND st.{filters['type']} = %s"
                params.append('Completed')
        
        # Add additional filters
        if filters['district']:
            base_query += " AND LOWER(s.district) = LOWER(%s)"
            params.append(filters['district'])
            
        if filters['center']:
            base_query += " AND LOWER(s.center) = LOWER(%s)"
            params.append(filters['center'])
            
        if filters['gender']:
            base_query += " AND s.gender = %s"
            params.append(filters['gender'])
            
        if filters['trade']:
            base_query += " AND s.trade = %s"
            params.append(filters['trade'])
        
        cursor.execute(base_query, params)
        students = cursor.fetchall()
        
        # Convert to CSV format
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'CAN ID', 'Student Name', "Father's Name", "Mother's Name", 'Batch ID',
            'Mobile', 'Religion', 'Category', 'DOB', 'District', 'Center', 'Gender',
            'Trade', 'One to One Counselling', 'Group Counselling', 'OJT Status', 'Guest Lecture',
            'Industrial Visit', 'Assessment', 'Assessment Date', 'School Enrollment',
            'Total Days', 'Attendance', 'Other Trainings',
            'Aadhar', 'Account Number', 'Account Holder', 'IFSC'
        ])
        
        # Write data
        for student in students:
            writer.writerow([
                student['can_id'], student['student_name'], student['father_name'], student['mother_name'],
                student['batch_id'], student['mobile'], student['religion'], student['category'],
                student['dob'].strftime('%d-%m-%Y') if student['dob'] else '',
                student['district'], student['center'], student['gender'],
                student['trade'], student['single_counselling'], student['group_counselling'],
                student['ojt'], student['guest_lecture'], student['industrial_visit'],
                student['assessment'],
                student['assessment_date'].strftime('%d-%m-%Y') if student['assessment_date'] else '',
                student['school_enrollment'], student['total_days'], student['attendance'],
                student['other_trainings'], student['aadhar'], student['account_number'],
                student['account_holder'], student['ifsc']
            ])
        
        # Create response
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=student_data.csv'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        print("Export error:", str(e))
        flash("An error occurred while exporting data", "error")
        return redirect(url_for('admin_dashboard'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.route('/reset_filters')
def reset_filters():
    # Clear all filters from session
    if 'filters' in session:
        for key in session['filters'].keys():
            session['filters'][key] = None
    return redirect(url_for('admin_dashboard'))
    
@app.route('/logout')
def logout():
    session.clear()
    response = redirect(url_for('front'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    flash("You have been logged out successfully", "success")
    return response



if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")