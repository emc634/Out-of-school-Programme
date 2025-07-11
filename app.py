from flask import Flask, render_template, request, flash, redirect, url_for, session,jsonify,send_file
import pandas as pd
from io import BytesIO
import openpyxl
import psycopg2
from psycopg2 import extras
from datetime import datetime
import json
from psycopg2 import IntegrityError, OperationalError

from functions import get_db_connection,age_calculator

app = Flask(__name__)
app.secret_key = 'bhuvnn'


course_days={
   "Agriculture":50,
   "Beauty & Wellness": 70,
   "Plumbing":70,
   "Food Processing":50,
   "Automotive":50,
   "Electronics":100,
   "Tourism & Hospitality" :66,
   "ITeS":65
}

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
            cursor.execute(
                "INSERT INTO students (can_id, student_name,batch_id, father_name, mother_name, mobile, religion, category, dob, district, center,gender, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (can_id, student_name,batch_id, father_name, mother_name, mobile, religion, category, dob, district, center, gender,password_hash)
            )
            cursor.execute(
                "INSERT INTO student_training (can_id, trade,total_days) VALUES (%s, %s, %s)",
                (can_id,trade,course_days[trade])
            )
            conn.commit()
            
            flash("Account created successfully", "success")
            return redirect(url_for("student_profile"))
            
        except IntegrityError as e:
            # Handle duplicate primary key (can_id) or NOT NULL violations
            if 'duplicate key value violates unique constraint' in str(e):
                flash("Candidate ID or Mobile No. already exists. Please use a different ID or Mobile No..", "error")
            else:
                flash("Data integrity error: " + str(e), "error")
            return redirect(url_for('student_signup'))

        except OperationalError as e:
            flash("Database operational error: " + str(e), "error")
            return redirect(url_for('student_signup'))

        except Exception as e:
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
            if user["password"]!=new_password:
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
        
        # Validate form inputs
        if not can_id or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("student_signin"))
        
        conn = None
        cursor = None
        try:
            # Connect to database
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                'SELECT * FROM students WHERE can_id = %s', 
                (can_id,)
            )
            user = cursor.fetchone()
            
            # Verify credentials
            if user is None or user['password']!= password:
                flash("Invalid CAN ID or password", "error")  # Updated message
                return redirect(url_for("student_signin"))
            
            # Successful login
            session['can_id'] = can_id  # Store CAN ID in session
            
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        
        except psycopg2.Error as e:
            flash("Database error. Please try again.", "error")
            return redirect(url_for("student_signin"))
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()  # Ensure connection always closes
        
    login_data=session.pop('can_id',{})
    return render_template("student_signin.html",login_data=login_data) 


#displaying profile
@app.route("/profile_display")
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
                update_fields_training.append("assessment = %s")
                update_values_training.append(assessment)
                update_fields_training.append("assessment_date = %s")
                update_values_training.append(datetime.today().date())

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
def dashboard():
    can_id = session.get('can_id')
    conn = None
    cursor = None
    student = None
    
    # Check if user is authenticated
    if not can_id:
        flash("Please log in to access the dashboard", "error")
        return redirect(url_for('student_signin'))
    
    if request.method == "POST":
        try:
            data = request.get_json()
            
            # Validate input data
            if not data:
                flash("No data provided", "error")
                return redirect(url_for('dashboard'))
            
            attended_days = data.get('attendedDays')
            
            # Validate attendance value
            if attended_days is None:
                flash("Attendance data is required", "error")
                return redirect(url_for('dashboard'))
            
            # Validate attendance range
            try:
                attended_days = int(attended_days)
                if attended_days < 0:
                    flash("Attendance cannot be negative", "error")
                    return redirect(url_for('dashboard'))
            except (ValueError, TypeError):
                flash("Invalid attendance format", "error")
                return redirect(url_for('dashboard'))
            
            # Database operations
            try:
                conn = get_db_connection()
                if not conn:
                    flash("Database connection failed", "error")
                    return redirect(url_for('dashboard'))
                
                cursor = conn.cursor()
                
                # Check if student exists and get current attendance
                cursor.execute('SELECT attendance FROM student_training WHERE can_id = %s', (can_id,))
                result = cursor.fetchone()
                if not result:
                    flash("Student not found", "error")
                    return redirect(url_for('dashboard'))
                
                # Update attendance
                cursor.execute('UPDATE student_training SET attendance = %s WHERE can_id = %s', (attended_days, can_id))
                
                if cursor.rowcount == 0:
                    flash("Failed to update attendance", "error")
                    return redirect(url_for('dashboard'))
                
                conn.commit()
                flash("Attendance updated successfully", "success")
                return redirect(url_for('dashboard'))
                
            except psycopg2.Error as e:
                if conn:
                    conn.rollback()
                flash(f"Database error: {str(e)}", "error")
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                if conn:
                    conn.rollback()
                flash("An unexpected error occurred while updating attendance", "error")
                return redirect(url_for('dashboard'))
            
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
                    
        except json.JSONDecodeError:
            flash("Invalid JSON format", "error")
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            flash("An unexpected error occurred", "error")
            return redirect(url_for('dashboard'))
    
    # GET request - Fetch student data
    try:
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed", "error")
            return render_template("dashboard.html", student=None, error="Database connection failed")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT attendance, single_counselling, group_counselling,total_days, ojt, industrial_visit, assessment, guest_lecture,school_enrollment,other_trainings
            FROM student_training 
            WHERE can_id = %s
        ''', (can_id,))
        student = cursor.fetchone()
        
        if not student:
            flash("Student data not found", "warning")
            return render_template("dashboard.html", student=None, error="Student data not found")
    
    except psycopg2.DatabaseError as e:
        flash(f"Database error: {str(e)}", "error")
        return render_template("dashboard.html", student=None, error="Database error occurred")
    
    except psycopg2.InterfaceError as e:
        flash("Database interface error", "error")
        return render_template("dashboard.html", student=None, error="Database connection issue")
    
    except psycopg2.OperationalError as e:
        flash("Database operational error", "error")
        return render_template("dashboard.html", student=None, error="Database is temporarily unavailable")
    
    except psycopg2.Error as e:
        flash(f"Database error: {str(e)}", "error")
        return render_template("dashboard.html", student=None, error="Database operation failed")
    
    except AttributeError as e:
        flash("Configuration error", "error")
        return render_template("dashboard.html", student=None, error="Application configuration issue")
    
    except Exception as e:
        flash("An unexpected error occurred while fetching data", "error")
        return render_template("dashboard.html", student=None, error="Internal server error")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template("dashboard.html", student=student)


@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        email=request.form.get("email")
        password=request.form.get('password')
        if not email or not password:
            flash("Please fill in both fields", "error")
            return redirect(url_for("admin_login"))
        
        try:
            conn = get_db_connection()
            if not conn:
                flash("Database connection failed", "error")
                return redirect(url_for('admin_login'))
            
            cursor = conn.cursor()
            
            
            # Check if admin exists and get current attendance
            cursor.execute('SELECT * FROM admins WHERE email = %s', (email,))
            result = cursor.fetchone()
            if not result:
                flash("Unexpected Email or Password, Please try again", "error")
                return redirect(url_for('admin_login'))
            
            flash("Login Successful","success")
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            print("Login error:", str(e))
            flash("An error occurred during login", "error")
            return redirect(url_for("admin_login"))

        finally:
            if conn:
                cursor.close()
                conn.close()
            
            
            
    return render_template('admin_login.html')





@app.route('/admin_dashboard')
def admin_dashboard():
    # Initialize session filters if not present
    if 'filters' not in session:
        session['filters'] = {
            'trade': None,
            'gender': None,
            'district': None,
            'center': None,
            'ojt_status': None,
            'school': None,
            'single_counselling': None,
            'group_counselling': None,
            'assessment': None,
            'industrial_visit': None
        }
    
    # Get current filters from session
    current_filters = session['filters']
    
    # Update filters from request parameters if provided
    for filter_name in current_filters.keys():
        if filter_name in request.args:
            value = request.args.get(filter_name)
            current_filters[filter_name] = value if value != '' else None
    
    # Save updated filters to session
    session['filters'] = current_filters
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 25  # Records per page
    
    try:
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed", "error")
            return render_template("admin_dashboard.html", 
                                 students=[], 
                                 total_records=0,
                                 page=1,
                                 total_pages=1,
                                 has_prev=False,
                                 has_next=False,
                                 current_filters=current_filters)
            
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        # Base query joining all three tables
        query = """
            SELECT 
                s.*, 
                st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                st.trade, st.total_days, st.attendance,
                bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
            FROM students s
            JOIN student_training st ON s.can_id = st.can_id
            JOIN bank_details bd ON s.can_id = bd.can_id
            WHERE 1=1
        """
        
        params = []
        
        # Apply filters with case-insensitive matching
        if current_filters['trade']:
            query += " AND LOWER(TRIM(st.trade)) = LOWER(%s)"
            params.append(current_filters['trade'].strip())
            
        if current_filters['gender']:
            query += " AND LOWER(TRIM(s.gender)) = LOWER(%s)"
            params.append(current_filters['gender'].strip())
            
        if current_filters['district']:
            query += " AND LOWER(TRIM(s.district)) = LOWER(%s)"
            params.append(current_filters['district'].strip())
            
        if current_filters['center']:
            query += " AND LOWER(TRIM(s.center)) = LOWER(%s)"
            params.append(current_filters['center'].strip())
            
        if current_filters['ojt_status']:
            query += " AND LOWER(TRIM(st.ojt)) = LOWER(%s)"
            params.append(current_filters['ojt_status'].strip())
        
        # Handle school enrollment filter
        if current_filters['school']:
            if current_filters['school'] == "Enrolled":
                query += " AND st.school_enrollment IS NOT NULL AND TRIM(st.school_enrollment) != ''"
            elif current_filters['school'] == "Not Enrolled":
                query += " AND (st.school_enrollment IS NULL OR TRIM(st.school_enrollment) = '')"
        
        if current_filters['single_counselling']:
            query += " AND LOWER(TRIM(st.single_counselling)) = LOWER(%s)"
            params.append(current_filters['single_counselling'].strip())
            
        if current_filters['group_counselling']:
            query += " AND LOWER(TRIM(st.group_counselling)) = LOWER(%s)"
            params.append(current_filters['group_counselling'].strip())
            
        if current_filters['assessment']:
            query += " AND LOWER(TRIM(st.assessment)) = LOWER(%s)"
            params.append(current_filters['assessment'].strip())
            
        if current_filters['industrial_visit']:
            query += " AND LOWER(TRIM(st.industrial_visit)) = LOWER(%s)"
            params.append(current_filters['industrial_visit'].strip())
        
        # Get total count for pagination
        count_query = query.replace(
            """SELECT 
                s.*, 
                st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                st.trade, st.total_days, st.attendance,
                bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc""",
            "SELECT COUNT(*)"
        )
        
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()[0]
        
        # Add pagination to main query
        query += " ORDER BY s.can_id LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        students = cursor.fetchall()
        
        # Calculate pagination info
        total_pages = max(1, (total_records + per_page - 1) // per_page)
        has_prev = page > 1
        has_next = page < total_pages
        
        # NEW: Get training counts for indicators (unfiltered)
        training_query = """
            SELECT 
                COUNT(*) AS total_students,
                SUM(CASE WHEN single_counselling = 'Completed' THEN 1 ELSE 0 END) AS single_completed,
                SUM(CASE WHEN group_counselling = 'Completed' THEN 1 ELSE 0 END) AS group_completed,
                SUM(CASE WHEN ojt = 'Completed' THEN 1 ELSE 0 END) AS ojt_completed,
                SUM(CASE WHEN guest_lecture = 'Completed' THEN 1 ELSE 0 END) AS guest_lecture_completed,
                SUM(CASE WHEN industrial_visit = 'Completed' THEN 1 ELSE 0 END) AS industrial_visit_completed,
                SUM(CASE WHEN assessment = 'Completed' THEN 1 ELSE 0 END) AS assessment_completed,
                SUM(CASE WHEN school_enrollment IS NOT NULL AND school_enrollment <> '' THEN 1 ELSE 0 END) AS school_enrollment_count
            FROM student_training
        """
        
        cursor.execute(training_query)
        training_counts = cursor.fetchone()
        
        return render_template(
            'admin_dashboard.html',
            students=students,
            total_records=total_records,
            training_counts=training_counts,  # Pass to template
            page=page,
            total_pages=total_pages,
            has_prev=has_prev,
            has_next=has_next,
            current_filters=current_filters
        )
        
    except Exception as e:
        print("Dashboard error:", str(e))
        flash("An error occurred while loading dashboard", "error")
        # Create empty training_counts on error
        training_counts = {
            'total_students': 0,
            'single_completed': 0,
            'group_completed': 0,
            'ojt_completed': 0,
            'guest_lecture_completed': 0,
            'industrial_visit_completed': 0,
            'assessment_completed': 0,
            'school_enrollment_count': 0
        }
        return render_template("admin_dashboard.html", 
                             students=[], 
                             total_records=0,
                             training_counts=training_counts,
                             page=1,
                             total_pages=1,
                             has_prev=False,
                             has_next=False,
                             current_filters=current_filters)
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/admin_dashboard/modal_data')
def modal_data():
    # Get parameters
    training_type = request.args.get('type')
    district = request.args.get('district', '').strip()
    center = request.args.get('center', '').strip()
    gender = request.args.get('gender', '').strip()
    trade = request.args.get('trade', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        base_query = """
            SELECT 
                s.*, 
                st.single_counselling, st.group_counselling, st.ojt, st.guest_lecture, 
                st.industrial_visit, st.assessment, st.assessment_date, st.school_enrollment, 
                st.trade, st.total_days, st.attendance,
                bd.aadhar, bd.account_number, bd.account_holder, bd.ifsc
            FROM students s
            JOIN student_training st ON s.can_id = st.can_id
            JOIN bank_details bd ON s.can_id = bd.can_id
            WHERE 1=1
        """
        
        params = []
        
        # Add training type condition
        if training_type != 'total':
            if training_type == 'school':
                base_query += " AND st.school_enrollment IS NOT NULL AND st.school_enrollment <> ''"
            else:
                base_query += f" AND st.{training_type} = %s"
                params.append('Completed')
        
        # Add additional filters
        if district:
            base_query += " AND LOWER(s.district) = LOWER(%s)"  # Case-insensitive
            params.append(district)
            
        if center:
            base_query += " AND LOWER(s.center) = LOWER(%s)"  # Case-insensitive
            params.append(center)
            
        if gender:
            base_query += " AND s.gender = %s"
            params.append(gender)
            
        if trade:
            base_query += " AND st.trade = %s"
            params.append(trade)
        
        cursor.execute(base_query, params)
        students = cursor.fetchall()
        
        # Convert to list of dicts for JSON serialization
        result = []
        for student in students:
            student_dict = dict(student)
            # Format dates
            if student_dict.get('dob'):
                student_dict['dob'] = student_dict['dob'].strftime('%d-%m-%Y')
            if student_dict.get('assessment_date'):
                student_dict['assessment_date'] = student_dict['assessment_date'].strftime('%d-%m-%Y')
            result.append(student_dict)
            
        return jsonify(result)
        
    except Exception as e:
        print("Modal data error:", str(e))
        return jsonify([])
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

@app.route('/download')
def download_excel():
    # 1. Connect to DB (replace with your DB)
    conn = get_db_connection()
    # 2. Query data
    tables = ['students', 'student_training', 'bank_details']
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine=openpyxl) as writer:
        for table in tables:
            # Query each table
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            # Write to Excel sheet (sheet name same as table name)
            df.to_excel(writer, index=False, sheet_name=table.capitalize())
    conn.close()
    output.seek(0)
    
    # 4. Send file to user
    return send_file(output,
                     download_name="data.xlsx",
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/download_excel')
def download_excel_route():
    return download_excel()

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully", "success")
    response = redirect(url_for('front'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response



if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")