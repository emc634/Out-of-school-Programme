from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file
import pandas as pd
import os
from datetime import datetime, date
import psycopg2
from dotenv import load_dotenv
from psycopg2 import extras
from psycopg2 import IntegrityError, OperationalError
from functools import wraps

# UPDATED IMPORT: Add IST time functions
from functions import get_db_connection, age_calculator, get_ist_time, get_ist_date

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

course_days = {
    "Agriculture": [50, "https://drive.google.com/file/d/1Ne5fPmmoC6W6JF92cIqe_uH40NXC5mCz/view?usp=drive_link"],
    "Beauty & Wellness": [70, "https://drive.google.com/file/d/1aI8JZfubWoA2cEeFl0BcyDQ7PZTHTtbC/view"],
    "Plumbing": [70, "https://drive.google.com/file/d/1tfs39122cJPT_JIU8Amj2F4LtYuazho0/view?usp=drive_link"],
    "Food Processing": [50, "https://drive.google.com/file/d/1RrPxtfiBjbs0ecYHK_5tVJbSUCkd3Dts/view?usp=drive_link"],
    "Automotive": [50, "https://drive.google.com/file/d/1wlYJdd5VgpxZnEhfw28D1AQ8RUZi98Cw/view?usp=drive_link"],
    "Electronics": [100, "https://drive.google.com/file/d/1VdM2kVZTTSZfSVSBkYRFYAqCZ_JanAkr/view?usp=drive_link"],
    "Tourism & Hospitality": [66, "https://drive.google.com/file/d/1o2yYeaCteillbpOh8FdsPedl03Gg06Xt/view?usp=drive_link"],
    "Retail": [65, "https://drive.google.com/file/d/1m9frLws3Aepqm1iEgZB_JlHti97jTE19/view?usp=drive_link"]
}

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
        if 'admin_id' not in session:
            return redirect(url_for('front'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def front():
    return render_template("front.html")

@app.route('/student_signup', methods=["GET", "POST"])
def student_signup():
    if request.method == "POST":
        student_name = request.form.get("studentName")
        father_name = request.form.get("fatherName")
        mother_name = request.form.get("motherName")
        batch_id = request.form.get("batchId")
        can_id = request.form.get("canId")
        mobile = request.form.get("mobile")
        religion = request.form.get("religion")
        category = request.form.get("category")
        dob = request.form.get('dob')
        district = request.form.get("district")
        center = request.form.get('center')
        trade = request.form.get("trade")
        gender = request.form.get("gender")
        password = request.form.get("password")
        confirmation = request.form.get("confirmPassword")

        session['form_data'] = {
            'student_name': student_name, 'father_name': father_name, 'mother_name': mother_name,
            'gender': gender, 'batch_id': batch_id, 'mobile': mobile, 'can_id': can_id,
            'religion': religion, 'category': category, 'dob': dob, 'district': district,
            'trade': trade, 'center': center
        }

        if not all([student_name, father_name, batch_id, mother_name, gender, mobile,
                    can_id, religion, category, dob, district, trade, center, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return redirect(url_for("student_signup"))

        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
            return redirect(url_for("student_signup"))

        if not mobile.isdigit() or len(mobile) != 10:
            flash("Mobile number must be exactly 10 digits", "error")
            return redirect(url_for("student_signup"))

        age = age_calculator(dob)
        if age < 14:
            flash("Candidate must be atleast 14 to sign up", "error")
            return redirect(url_for("student_signup"))

        if age >= 18:
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
            conn.autocommit = False

            cursor.execute("SELECT can_id FROM students WHERE mobile = %s", (mobile,))
            if cursor.fetchone():
                flash("Mobile number already registered", "error")
                return redirect(url_for("student_signup"))

            cursor.execute("""
                INSERT INTO students 
                (can_id, student_name, batch_id, father_name, mother_name, 
                 mobile, trade, religion, category, dob, district, center, gender, password) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (can_id, student_name, batch_id, father_name, mother_name,
                  mobile, trade, religion, category, dob, district, center, gender, password_hash))

            cursor.execute(
                "INSERT INTO student_training (can_id, total_days) VALUES (%s, %s)",
                (can_id, course_days[trade][0])
            )

            conn.commit()
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

    form_data = session.pop('form_data', {})
    return render_template('student_signup.html', form_data=form_data)

@app.route('/student_profile', methods=["GET", "POST"])
@login_required
def student_profile():
    form_data = session.get("form_data", {})

    if request.method == "POST":
        can_id = form_data.get('can_id')
        aadhar = request.form.get('aadhar')
        account_number = request.form.get('accountNumber')
        account_holder = request.form.get("accountHolder")
        ifsc = request.form.get('ifsc')

        current_data = {
            'aadhar': aadhar, 'account_number': account_number,
            'account_holder': account_holder, 'ifsc': ifsc
        }

        merged_data = {**form_data, **current_data}
        session['form_data'] = merged_data

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
                           (can_id, aadhar, account_number, account_holder, ifsc))

            conn.commit()
            flash("Profile Completion Successful", "success")
            session['can_id'] = form_data.get('can_id')
            session.pop('form_data', None)
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

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('student_profile'))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    form_data = session.get('form_data', {})
    return render_template('student_profile.html', form_data=form_data)

@app.route("/reset_password", methods=["GET", "POST"])
@login_required
def reset_password():
    can_id = session.get('can_id')
    if not can_id:
        flash("Please login to access this page", "error")
        return redirect(url_for('student_signin'))

    if request.method == "POST":
        current_password = request.form.get("currentPassword")
        new_password = request.form.get("newPassword")
        confirm_password = request.form.get("confirmPassword")

        if not all([current_password, new_password, confirm_password]):
            flash("Please fill in all password fields", "error")
            return redirect(url_for("reset_password"))

        if new_password != confirm_password:
            flash("New passwords don't match. Please try again.", "error")
            return redirect(url_for("reset_password"))

        if current_password == new_password:
            flash("New password must be different from current password", "error")
            return redirect(url_for("reset_password"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute('SELECT password FROM students WHERE can_id = %s', (can_id,))
            user = cursor.fetchone()

            if user is None:
                flash("User not found. Please login again.", "error")
                session.pop('can_id', None)
                return redirect(url_for("student_signin"))

            if user["password"] != current_password:
                flash("Current password is incorrect", "error")
                return redirect(url_for("reset_password"))

            cursor.execute('UPDATE students SET password = %s WHERE can_id = %s', (new_password, can_id))
            conn.commit()

            flash("Password updated successfully!", "success")
            return redirect(url_for('profile_display'))

        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('reset_password'))

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("reset_password.html")

@app.route("/student_signin", methods=["GET", "POST"])
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

    login_data = session.get('can_id', '')
    return render_template("student_signin.html", login_data=login_data)

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
    training = cursor.fetchone()
    cursor.execute('SELECT * FROM bank_details WHERE can_id = %s', (can_id,))
    bank = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("profile_display.html", student=student, bank=bank, training=training)

@app.route("/update_profile", methods=["GET", "POST"])
def update_profile():
    can_id = session.get('can_id')
    if not can_id:
        flash("Please login to access this page", "error")
        return redirect(url_for('student_signin'))

    if request.method == "POST":
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

        session['update_form_data'] = {
            'studentName': student_name, 'fatherName': father_name, 'motherName': mother_name,
            'dob': dob, 'gender': gender, 'religion': religion, 'category': category,
            'mobile': mobile, 'ojt': ojt, 'guest_lecture': guest_lecture,
            'industrial_visit': industrial_visit, 'assessment': assessment,
            'group_counselling': group_counselling, 'single_counselling': single_counselling,
            'school_enrollment': school_name, 'udsi': udsi, 'other_trainings': other_trainings,
            'ifsc': ifsc, 'account_number': account_number, 'account_holder': account_holder
        }

        if mobile and (not mobile.isdigit() or len(mobile) != 10):
            flash("Please enter a valid 10-digit mobile number", "error")
            return redirect(url_for("update_profile"))

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute('SELECT password FROM students WHERE can_id = %s', (can_id,))
            user = cursor.fetchone()
            if not user:
                flash("User not found. Please login again.", "error")
                session.pop('can_id', None)
                return redirect(url_for("student_signin"))

            if mobile:
                cursor.execute('SELECT can_id FROM students WHERE mobile = %s AND can_id != %s', (mobile, can_id))
                if cursor.fetchone():
                    flash("Mobile number already registered with another account", "error")
                    return redirect(url_for("update_profile"))

            update_fields_student, update_values_student = [], []
            update_fields_training, update_values_training = [], []
            update_fields_bank, update_values_bank = [], []

            for field, value, col in [
                (student_name, student_name, "student_name"), (father_name, father_name, "father_name"),
                (mother_name, mother_name, "mother_name"), (dob, dob, "dob"),
                (gender, gender, "gender"), (religion, religion, "religion"),
                (category, category, "category"), (mobile, mobile, "mobile")
            ]:
                if value:
                    update_fields_student.append(f"{col} = %s")
                    update_values_student.append(value)

            for field, col in [
                (single_counselling, "single_counselling"), (group_counselling, "group_counselling"),
                (other_trainings, "other_trainings"), (ojt, "ojt"),
                (guest_lecture, "guest_lecture"), (industrial_visit, "industrial_visit")
            ]:
                if field:
                    update_fields_training.append(f"{col} = %s")
                    update_values_training.append(field)

            if assessment:
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
                    # UPDATED: Use IST date
                    update_values_training.append(get_ist_date())
                else:
                    flash("Assessment cannot be updated because your attendance is below 80%.", "error")
                    return redirect(url_for("update_profile"))

            if school_name:
                update_fields_training.append("school_enrollment = %s")
                update_values_training.append(school_name)
            if udsi:
                update_fields_training.append("udsi = %s")
                update_values_training.append(udsi)

            if account_number:
                update_fields_bank.append("account_number = %s")
                update_values_bank.append(account_number)
            if ifsc:
                update_fields_bank.append("ifsc = %s")
                update_values_bank.append(ifsc)
            if account_holder:
                update_fields_bank.append("account_holder = %s")
                update_values_bank.append(account_holder)

            if "udsi = %s" in update_fields_training and "school_enrollment = %s" not in update_fields_training:
                flash('UDSI code cannot be filled without filling Enrolled School section', 'error')
                return redirect(url_for('update_profile'))
            if "school_enrollment = %s" in update_fields_training and "udsi = %s" not in update_fields_training:
                flash('Please make sure you fill the UDSI code of your Enrolled School too', 'error')
                return redirect(url_for('update_profile'))

            if not (update_fields_student or update_fields_training or update_fields_bank):
                flash('No changes detected. Please modify at least one field.', 'info')
                return redirect(url_for('update_profile'))

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

            conn.commit()
            session.pop('update_form_data', None)
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile_display'))

        except IntegrityError as e:
            if "mobile" in str(e).lower():
                flash("Mobile number already registered", "error")
            else:
                flash(f"Database integrity error: {str(e)}", "error")
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirect(url_for('update_profile'))

    form_data = session.get('update_form_data', {})
    return render_template('update_profile.html', form_data=form_data)

# UPDATED DASHBOARD ROUTE with IST
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

            # UPDATED: Use IST date
            today_ist = get_ist_date()

            # Check if already marked today
            cursor.execute("""
                SELECT last_attendance_date FROM student_training
                WHERE can_id = %s
            """, (can_id,))

            result = cursor.fetchone()

            if result and result['last_attendance_date'] == today_ist:
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

            # UPDATED: Get IST timestamp without microseconds
            ist_timestamp = get_ist_time()

            # Update attendance in student_training
            new_attendance = current_attendance + 1
            cursor.execute("""
                UPDATE student_training 
                SET attendance = %s, last_attendance_date = %s
                WHERE can_id = %s
            """, (new_attendance, today_ist, can_id))

            # UPDATED: Record in daily_attendance with IST timestamp
            cursor.execute("""
                INSERT INTO daily_attendance (can_id, attendance_date, status, marked_at)
                VALUES (%s, %s, 'Present', %s)
                ON CONFLICT (can_id, attendance_date) DO NOTHING
            """, (can_id, today_ist, ist_timestamp))

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
            return render_template("dashboard.html", student=None, today_date=get_ist_date())

    except Exception as e:
        flash("An unexpected error occurred while fetching data", "error")
        return render_template("dashboard.html", student=None, today_date=get_ist_date())

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # UPDATED: Pass IST date to template
    return render_template("dashboard.html", student=student, today_date=get_ist_date())

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get('password')

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

            session['admin_id'] = admin['id']
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
    current_filters = {key: request.args.get(key) for key in [
        'trade', 'gender', 'district', 'center', 'ojt_status',
        'school', 'single_counselling', 'group_counselling',
        'assessment', 'industrial_visit', 'other_trainings'
    ]}

    default_counts = {
        'total_students': 0, 'single_completed': 0, 'group_completed': 0,
        'ojt_completed': 0, 'guest_lecture_completed': 0, 'industrial_visit_completed': 0,
        'assessment_completed': 0, 'school_enrollment_count': 0, 'other_training_completed': 0
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        # --- Training counts query ---
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

        # --- TODAY'S attendance count using attendance_date ---
        today = get_ist_date()  # Should return YYYY-MM-DD
        
        # Build attendance query with same filters
        attendance_query = """
            SELECT COUNT(*) 
            FROM daily_attendance da
            JOIN students s ON da.can_id = s.can_id
            LEFT JOIN student_training st ON s.can_id = st.can_id
            WHERE da.attendance_date = %s AND da.status = 'Present'
        """
        attendance_params = [today]
        
        # Apply the same filters to attendance query
        for key, condition in filter_map.items():
            value = current_filters.get(key)
            if value:
                attendance_query += f" AND {condition}"
                attendance_params.append(value.strip())
        
        if current_filters.get('school'):
            if current_filters['school'] == "Enrolled":
                attendance_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
            elif current_filters['school'] == "Not Enrolled":
                attendance_query += " AND (st.school_enrollment IS NULL OR TRIM(st.school_enrollment) = '')"

        if current_filters.get('other_trainings'):
            if current_filters['other_trainings'] == "Not Completed":
                attendance_query += " AND (st.other_trainings IS NULL OR LOWER(TRIM(st.other_trainings)) = 'not completed')"
            else:
                attendance_query += " AND LOWER(TRIM(st.other_trainings)) = LOWER(%s)"
                attendance_params.append(current_filters['other_trainings'].strip())
        
        cursor.execute(attendance_query, attendance_params)
        todays_attendance_count = cursor.fetchone()[0] or 0
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


# FIXED MODAL DATA ROUTE with debugging
@app.route('/admin_dashboard/modal_data')
def modal_data():
    # Collect ALL filter parameters from the request
    training_type = request.args.get('type', '').strip()
    district = request.args.get('district', '').strip()
    center = request.args.get('center', '').strip()
    gender = request.args.get('gender', '').strip()
    trade = request.args.get('trade', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    # Additional dashboard filters
    ojt_status = request.args.get('ojt_status', '').strip()
    school = request.args.get('school', '').strip()
    single_counselling = request.args.get('single_counselling', '').strip()
    group_counselling = request.args.get('group_counselling', '').strip()
    assessment = request.args.get('assessment', '').strip()
    industrial_visit = request.args.get('industrial_visit', '').strip()
    other_trainings = request.args.get('other_trainings', '').strip()

    # DEBUG: Print filters
    print("\n========== MODAL FILTERS ==========")
    if training_type: print(f"type: '{training_type}'")
    if district: print(f"district: '{district}'")
    if center: print(f"center: '{center}'")
    if gender: print(f"gender: '{gender}'")
    if trade: print(f"trade: '{trade}'")
    if date_filter: print(f"date: '{date_filter}'")
    if ojt_status: print(f"ojt_status: '{ojt_status}'")
    if school: print(f"school: '{school}'")
    if single_counselling: print(f"single_counselling: '{single_counselling}'")
    if group_counselling: print(f"group_counselling: '{group_counselling}'")
    if assessment: print(f"assessment: '{assessment}'")
    if industrial_visit: print(f"industrial_visit: '{industrial_visit}'")
    if other_trainings: print(f"other_trainings: '{other_trainings}'")
    print("====================================\n")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        # Special handling for TODAY'S ATTENDANCE
        if training_type == 'todays_attendance':
            base_query = """
                SELECT DISTINCT
                    s.*, 
                    st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                    st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                    st.total_days, st.attendance, st.other_trainings, st.udsi,
                    bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
                FROM students s
                LEFT JOIN student_training st ON s.can_id = st.can_id
                LEFT JOIN bank_details bd ON s.can_id = bd.can_id
                WHERE s.can_id IN (
                    SELECT can_id FROM daily_attendance 
                    WHERE attendance_date = %s AND status = 'Present'
                )
            """
            today_date = date_filter if date_filter else get_ist_date()
            params = [today_date]
            print(f"Attendance date: {today_date}")
        else:
            # Regular query (non-attendance)
            base_query = """
                SELECT 
                    s.*, 
                    st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                    st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                    st.total_days, st.attendance, st.other_trainings, st.udsi,
                    bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
                FROM students s
                LEFT JOIN student_training st ON s.can_id = st.can_id
                LEFT JOIN bank_details bd ON s.can_id = bd.can_id
                WHERE 1=1
            """
            params = []

        # Apply TRAINING TYPE filter - FIX: Don't apply duplicate filters
        if training_type and training_type != 'total' and training_type != 'todays_attendance':
            if training_type == 'school':
                base_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
            elif training_type == 'other_trainings':
                base_query += " AND st.other_trainings IS NOT NULL AND TRIM(st.other_trainings) <> ''"
            else:
                base_query += f" AND st.{training_type} = %s"
                params.append('Completed')

        # Apply DISTRICT filter
        if district:
            base_query += " AND LOWER(TRIM(s.district)) = LOWER(TRIM(%s))"
            params.append(district)

        # Apply CENTER filter
        if center:
            base_query += " AND LOWER(TRIM(s.center)) = LOWER(TRIM(%s))"
            params.append(center)

        # Apply GENDER filter
        if gender:
            base_query += " AND LOWER(TRIM(s.gender)) = LOWER(TRIM(%s))"
            params.append(gender)

        # Apply TRADE filter
        if trade:
            base_query += " AND LOWER(TRIM(s.trade)) = LOWER(TRIM(%s))"
            params.append(trade)
        
        # FIX: Only apply these if they're NOT the main training_type
        # Apply OJT STATUS filter (only if not the main type)
        if ojt_status and training_type != 'ojt':
            base_query += " AND LOWER(TRIM(st.ojt)) = LOWER(TRIM(%s))"
            params.append(ojt_status)
        
        # Apply SINGLE COUNSELLING filter (only if not the main type)
        if single_counselling and training_type != 'single_counselling':
            base_query += " AND LOWER(TRIM(st.single_counselling)) = LOWER(TRIM(%s))"
            params.append(single_counselling)
        
        # Apply GROUP COUNSELLING filter (only if not the main type)
        if group_counselling and training_type != 'group_counselling':
            base_query += " AND LOWER(TRIM(st.group_counselling)) = LOWER(TRIM(%s))"
            params.append(group_counselling)
        
        # Apply ASSESSMENT filter (only if not the main type)
        if assessment and training_type != 'assessment':
            base_query += " AND LOWER(TRIM(st.assessment)) = LOWER(TRIM(%s))"
            params.append(assessment)
        
        # Apply INDUSTRIAL VISIT filter (only if not the main type)
        if industrial_visit and training_type != 'industrial_visit':
            base_query += " AND LOWER(TRIM(st.industrial_visit)) = LOWER(TRIM(%s))"
            params.append(industrial_visit)
        
        # Apply SCHOOL ENROLLMENT filter (only if not the main type)
        if school and training_type != 'school':
            if school == "Enrolled":
                base_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
            elif school == "Not Enrolled":
                base_query += " AND (st.school_enrollment IS NULL OR TRIM(st.school_enrollment) = '')"
        
        # Apply OTHER TRAININGS filter (only if not the main type)
        if other_trainings and training_type != 'other_trainings':
            if other_trainings == "Not Completed":
                base_query += " AND (st.other_trainings IS NULL OR LOWER(TRIM(st.other_trainings)) = 'not completed')"
            else:
                base_query += " AND LOWER(TRIM(st.other_trainings)) = LOWER(TRIM(%s))"
                params.append(other_trainings)

        # DEBUG: Print query
        print("\n========== SQL QUERY ==========")
        print(base_query)
        print("\n========== PARAMS ==========")
        print(params)
        print("================================\n")

        # Execute query
        cursor.execute(base_query, params)
        students = cursor.fetchall()
        
        print(f"\n========== RESULTS: {len(students)} records found ==========\n")
        
        # Get attendance details separately for attendance modal
        attendance_details = {}
        if training_type == 'todays_attendance':
            today_date = date_filter if date_filter else get_ist_date()
            cursor.execute("""
                SELECT can_id, attendance_date, marked_at, status
                FROM daily_attendance
                WHERE attendance_date = %s AND status = 'Present'
            """, (today_date,))
            attendance_records = cursor.fetchall()
            for record in attendance_records:
                attendance_details[record['can_id']] = {
                    'attendance_date': record['attendance_date'],
                    'marked_at': record['marked_at'],
                    'status': record['status']
                }

        # Calculate gender statistics
        total_count = len(students)
        male_count = sum(1 for student in students if student.get('gender', '').lower() == 'male')
        female_count = sum(1 for student in students if student.get('gender', '').lower() == 'female')
        other_count = total_count - male_count - female_count

        male_percentage = (male_count / total_count * 100) if total_count > 0 else 0
        female_percentage = (female_count / total_count * 100) if total_count > 0 else 0
        other_percentage = (other_count / total_count * 100) if total_count > 0 else 0

        # Build result array with safe date formatting
        result = []
        for student in students:
            student_dict = dict(student)
            
            # Safe date formatting with None checks
            if student_dict.get('dob'):
                student_dict['dob'] = student_dict['dob'].strftime('%d-%m-%Y')
            else:
                student_dict['dob'] = ''
                
            if student_dict.get('assessment_date'):
                student_dict['assessment_date'] = student_dict['assessment_date'].strftime('%d-%m-%Y')
            else:
                student_dict['assessment_date'] = ''
            
            # Add attendance details if this is attendance modal
            if training_type == 'todays_attendance' and student_dict['can_id'] in attendance_details:
                att_detail = attendance_details[student_dict['can_id']]
                
                # Safe date formatting for attendance fields
                if att_detail.get('attendance_date'):
                    student_dict['attendance_date'] = att_detail['attendance_date'].strftime('%d-%m-%Y')
                else:
                    student_dict['attendance_date'] = ''
                
                if att_detail.get('marked_at'):
                    student_dict['marked_at'] = att_detail['marked_at'].strftime('%d-%m-%Y %H:%M:%S')
                else:
                    student_dict['marked_at'] = ''
                    
                student_dict['status'] = att_detail.get('status', '')
            
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
        import traceback
        traceback.print_exc()
        return jsonify({'students': [], 'gender_stats': {
            'total': 0,
            'male': {'count': 0, 'percentage': 0},
            'female': {'count': 0, 'percentage': 0},
            'other': {'count': 0, 'percentage': 0}
        }}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/export_filtered_data')
def export_filtered_data():
    # Collect ALL possible filter parameters from the request
    filters = {
        'type': request.args.get('type', 'total').strip(),
        'district': request.args.get('district', '').strip(),
        'center': request.args.get('center', '').strip(),
        'gender': request.args.get('gender', '').strip(),
        'trade': request.args.get('trade', '').strip(),
        'ojt_status': request.args.get('ojt_status', '').strip(),
        'school': request.args.get('school', '').strip(),
        'single_counselling': request.args.get('single_counselling', '').strip(),
        'group_counselling': request.args.get('group_counselling', '').strip(),
        'assessment': request.args.get('assessment', '').strip(),
        'industrial_visit': request.args.get('industrial_visit', '').strip(),
        'other_trainings': request.args.get('other_trainings', '').strip(),
        'date': request.args.get('date', '').strip()
    }

    # DEBUG: Print filters
    print("\n========== EXPORT FILTERS ==========")
    for key, value in filters.items():
        if value:
            print(f"{key}: '{value}'")
    print("====================================\n")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        # Special handling for TODAY'S ATTENDANCE export
        if filters['type'] == 'todays_attendance':
            base_query = """
                SELECT DISTINCT
                    s.can_id, s.student_name, s.father_name, s.mother_name, s.batch_id,
                    s.mobile, s.religion, s.category, s.dob, s.district, s.center, s.gender,
                    s.trade, st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture,
                    st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment,
                    st.total_days, st.attendance, st.other_trainings, st.udsi,
                    bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc,
                    da.attendance_date, da.marked_at, da.status
                FROM students s
                LEFT JOIN student_training st ON s.can_id = st.can_id
                LEFT JOIN bank_details bd ON s.can_id = bd.can_id
                INNER JOIN daily_attendance da ON s.can_id = da.can_id
                WHERE da.status = 'Present' AND da.attendance_date = %s
            """
            # Use provided date or today's IST date
            attendance_date = filters['date'] if filters['date'] else get_ist_date()
            params = [attendance_date]
            print(f"Attendance date filter: {attendance_date}")
        else:
            # Regular export query (non-attendance)
            base_query = """
                SELECT 
                    s.can_id, s.student_name, s.father_name, s.mother_name, s.batch_id,
                    s.mobile, s.religion, s.category, s.dob, s.district, s.center, s.gender,
                    s.trade, st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture,
                    st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment,
                    st.total_days, st.attendance, st.other_trainings, st.udsi,
                    bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
                FROM students s
                LEFT JOIN student_training st ON s.can_id = st.can_id
                LEFT JOIN bank_details bd ON s.can_id = bd.can_id
                WHERE 1=1
            """
            params = []

            # Apply TYPE filter - FIX: Don't add extra conditions if type is already being filtered
            if filters['type'] != 'total':
                if filters['type'] == 'school':
                    base_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
                elif filters['type'] == 'other_trainings':
                    base_query += " AND st.other_trainings IS NOT NULL AND TRIM(st.other_trainings) <> ''"
                else:
                    # For single_counselling, group_counselling, ojt, guest_lecture, industrial_visit, assessment
                    base_query += f" AND st.{filters['type']} = %s"
                    params.append('Completed')

        # Apply DISTRICT filter
        if filters['district']:
            base_query += " AND LOWER(TRIM(s.district)) = LOWER(TRIM(%s))"
            params.append(filters['district'])

        # Apply CENTER filter
        if filters['center']:
            base_query += " AND LOWER(TRIM(s.center)) = LOWER(TRIM(%s))"
            params.append(filters['center'])

        # Apply GENDER filter
        if filters['gender']:
            base_query += " AND LOWER(TRIM(s.gender)) = LOWER(TRIM(%s))"
            params.append(filters['gender'])

        # Apply TRADE filter
        if filters['trade']:
            base_query += " AND LOWER(TRIM(s.trade)) = LOWER(TRIM(%s))"
            params.append(filters['trade'])
        
        # FIX: Only apply these filters if they're NOT the main 'type' filter
        # Apply OJT STATUS filter (only if it's not the type)
        if filters['ojt_status'] and filters['type'] != 'ojt':
            base_query += " AND LOWER(TRIM(st.ojt)) = LOWER(TRIM(%s))"
            params.append(filters['ojt_status'])
        
        # Apply SINGLE COUNSELLING filter (only if it's not the type)
        if filters['single_counselling'] and filters['type'] != 'single_counselling':
            base_query += " AND LOWER(TRIM(st.single_counselling)) = LOWER(TRIM(%s))"
            params.append(filters['single_counselling'])
        
        # Apply GROUP COUNSELLING filter (only if it's not the type)
        if filters['group_counselling'] and filters['type'] != 'group_counselling':
            base_query += " AND LOWER(TRIM(st.group_counselling)) = LOWER(TRIM(%s))"
            params.append(filters['group_counselling'])
        
        # Apply ASSESSMENT filter (only if it's not the type)
        if filters['assessment'] and filters['type'] != 'assessment':
            base_query += " AND LOWER(TRIM(st.assessment)) = LOWER(TRIM(%s))"
            params.append(filters['assessment'])
        
        # Apply INDUSTRIAL VISIT filter (only if it's not the type)
        if filters['industrial_visit'] and filters['type'] != 'industrial_visit':
            base_query += " AND LOWER(TRIM(st.industrial_visit)) = LOWER(TRIM(%s))"
            params.append(filters['industrial_visit'])
        
        # Apply SCHOOL ENROLLMENT filter (only if it's not the type)
        if filters['school'] and filters['type'] != 'school':
            if filters['school'] == "Enrolled":
                base_query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) <> ''"
            elif filters['school'] == "Not Enrolled":
                base_query += " AND (st.school_enrollment IS NULL OR TRIM(st.school_enrollment) = '')"
        
        # Apply OTHER TRAININGS filter (only if it's not the type)
        if filters['other_trainings'] and filters['type'] != 'other_trainings':
            if filters['other_trainings'] == "Not Completed":
                base_query += " AND (st.other_trainings IS NULL OR LOWER(TRIM(st.other_trainings)) = 'not completed')"
            else:
                base_query += " AND LOWER(TRIM(st.other_trainings)) = LOWER(TRIM(%s))"
                params.append(filters['other_trainings'])

        # DEBUG: Print the final query and params
        print("\n========== SQL QUERY ==========")
        print(base_query)
        print("\n========== PARAMS ==========")
        print(params)
        print("================================\n")

        # Execute the query
        cursor.execute(base_query, params)
        students = cursor.fetchall()

        # DEBUG: Print result count
        print(f"\n========== RESULTS: {len(students)} records found ==========\n")

        # If no results, let's check what data actually exists
        if not students or len(students) == 0:
            # Debug query to see what values exist in database
            print("\n========== DEBUGGING: Checking existing values ==========")
            
            if filters['district']:
                cursor.execute("SELECT DISTINCT TRIM(district) as district FROM students ORDER BY district")
                districts = [row['district'] for row in cursor.fetchall()]
                print(f"Available districts: {districts}")
                print(f"Looking for: '{filters['district']}'")
            
            if filters['trade']:
                cursor.execute("SELECT DISTINCT TRIM(trade) as trade FROM students ORDER BY trade")
                trades = [row['trade'] for row in cursor.fetchall()]
                print(f"Available trades: {trades}")
                print(f"Looking for: '{filters['trade']}'")
            
            if filters['gender']:
                cursor.execute("SELECT DISTINCT TRIM(gender) as gender FROM students ORDER BY gender")
                genders = [row['gender'] for row in cursor.fetchall()]
                print(f"Available genders: {genders}")
                print(f"Looking for: '{filters['gender']}'")
            
            print("=========================================================\n")
            
            flash("No data found matching the selected filters. Please adjust your filters and try again.", "warning")
            return redirect(url_for('admin_dashboard'))

        # Create CSV in memory
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write CSV headers (different for attendance vs regular export)
        if filters['type'] == 'todays_attendance':
            writer.writerow([
                'CAN ID', 'Student Name', "Father's Name", "Mother's Name", 'Batch ID',
                'Mobile', 'Religion', 'Category', 'DOB', 'District', 'Center', 'Gender',
                'Trade', 'One to One Counselling', 'Group Counselling', 'OJT Status', 'Guest Lecture',
                'Industrial Visit', 'Assessment', 'Assessment Date', 'School Enrollment', 'UDSI',
                'Total Days', 'Attendance', 'Other Trainings',
                'Aadhar', 'Account Number', 'Account Holder', 'IFSC',
                'Attendance Date', 'Marked At', 'Status'
            ])
        else:
            writer.writerow([
                'CAN ID', 'Student Name', "Father's Name", "Mother's Name", 'Batch ID',
                'Mobile', 'Religion', 'Category', 'DOB', 'District', 'Center', 'Gender',
                'Trade', 'One to One Counselling', 'Group Counselling', 'OJT Status', 'Guest Lecture',
                'Industrial Visit', 'Assessment', 'Assessment Date', 'School Enrollment', 'UDSI',
                'Total Days', 'Attendance', 'Other Trainings',
                'Aadhar', 'Account Number', 'Account Holder', 'IFSC'
            ])

        # Write data rows
        for student in students:
            # Safe date formatting with None checks
            dob_str = student['dob'].strftime('%d-%m-%Y') if student.get('dob') else ''
            assessment_date_str = student['assessment_date'].strftime('%d-%m-%Y') if student.get('assessment_date') else ''
            
            # Build base row data
            row_data = [
                student.get('can_id', ''),
                student.get('student_name', ''),
                student.get('father_name', ''),
                student.get('mother_name', ''),
                student.get('batch_id', ''),
                student.get('mobile', ''),
                student.get('religion', ''),
                student.get('category', ''),
                dob_str,
                student.get('district', ''),
                student.get('center', ''),
                student.get('gender', ''),
                student.get('trade', ''),
                student.get('single_counselling', ''),
                student.get('group_counselling', ''),
                student.get('ojt', ''),
                student.get('guest_lecture', ''),
                student.get('industrial_visit', ''),
                student.get('assessment', ''),
                assessment_date_str,
                student.get('school_enrollment', ''),
                student.get('udsi', ''),
                student.get('total_days', ''),
                student.get('attendance', ''),
                student.get('other_trainings', ''),
                student.get('aadhar', ''),
                student.get('account_number', ''),
                student.get('account_holder', ''),
                student.get('ifsc', '')
            ]
            
            # Add attendance-specific columns if this is an attendance export
            if filters['type'] == 'todays_attendance':
                attendance_date_str = student['attendance_date'].strftime('%d-%m-%Y') if student.get('attendance_date') else ''
                marked_at_str = student['marked_at'].strftime('%d-%m-%Y %H:%M:%S') if student.get('marked_at') else ''
                row_data.extend([
                    attendance_date_str,
                    marked_at_str,
                    student.get('status', '')
                ])
            
            writer.writerow(row_data)

        # Generate descriptive filename based on filters
        filename_parts = ['student_data']
        
        if filters['type'] == 'todays_attendance':
            filename_parts.append('attendance')
            if filters['date']:
                filename_parts.append(filters['date'].replace('-', '_'))
        elif filters['type'] != 'total':
            filename_parts.append(filters['type'].replace('_', '-'))
        
        if filters['district']:
            filename_parts.append(filters['district'].replace(' ', '-'))
        if filters['trade']:
            filename_parts.append(filters['trade'].replace(' ', '-'))
        if filters['center']:
            filename_parts.append(filters['center'].replace(' ', '-'))
            
        filename = '_'.join(filename_parts) + '.csv'
        
        # Create and return response
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-type'] = 'text/csv'

        print(f"✅ Export successful: {filename} ({len(students)} records)\n")
        return response

    except Exception as e:
        print("Export error:", str(e))
        import traceback
        traceback.print_exc()
        flash(f"An error occurred while exporting data: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/reset_filters')
def reset_filters():
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