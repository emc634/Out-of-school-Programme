from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
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
def index():
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
             
        password_hash = generate_password_hash(password)
        
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
            if not check_password_hash(user['password'], current_password):
                flash("Current password is incorrect", "error")
                return redirect(url_for("reset_password"))
            
            # Hash the new password
            new_password_hash = generate_password_hash(new_password)
            
            # Update password in database
            cursor.execute(
                'UPDATE students SET password = %s WHERE can_id = %s',
                (new_password_hash, can_id)
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
            if user is None or not check_password_hash(user['password'], password):
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
        # Get form data
        student_name = request.form.get("studentName")   
        father_name = request.form.get("fatherName")
        mother_name = request.form.get("motherName")
        dob = request.form.get("dob")
        gender = request.form.get("gender")
        religion = request.form.get("religion")
        category = request.form.get("category")
        mobile = request.form.get("mobile")
        single_counselling=request.form.get("single_counselling")
        group_counselling=request.form.get("group_counselling")
        ojt=request.form.get('ojt')
        guest_lecture=request.form.get('guestLecture')
        industrial_visit=request.form.get('industrialVisit')
        other_trainings=request.form.get('other_trainings')
        assessment=request.form.get('assessment')
        school_name=request.form.get('schoolName').upper()
        udsi=request.form.get('udsicode')
        account_number=request.form.get('accountNumber')
        account_holder=request.form.get('accountHolder')
        ifsc=request.form.get('ifsc')
        
        # Store form data in session (excluding password)
        session['update_form_data'] = {
            'studentName': student_name,
            'fatherName': father_name,
            'motherName': mother_name,
            'dob': dob,
            'gender': gender,
            'religion': religion,
            'category': category,
            'mobile': mobile,
            'ojt':ojt,
            'guest_lecture':guest_lecture,
            'industrial_visit':industrial_visit,
            'assessment':assessment,
            'group_counselling':group_counselling,
            'single_counselling':single_counselling,
            'school_enrollment':school_name,
            'udsi':udsi,
            'other_trainings':other_trainings,
            'ifsc':ifsc,
            'account_number':account_number,
            'account_holder':account_holder
        }
        
        
        # Validate mobile number format (if provided)
        if mobile and (not mobile.isdigit() or len(mobile) != 10):
            flash("Please enter a valid 10-digit mobile number", "error")
            return redirect(url_for("update_profile"))
        
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
            
            
            # Check if mobile number already exists for other users (if mobile is being updated)
            if mobile:
                cursor.execute(
                    'SELECT can_id FROM students WHERE mobile = %s AND can_id != %s', 
                    (mobile, can_id)
                )
                existing_mobile = cursor.fetchone()
                
                if existing_mobile:
                    flash("Mobile number already registered with another account", "error")
                    return redirect(url_for("update_profile"))
            
            # Build dynamic UPDATE query based on provided fields
            update_fields_student = []
            update_values_student = []
            
            update_fields_training = []
            update_values_training = []
            
            update_fields_bank = []
            update_values_bank = []
            
            if student_name:
                update_fields_student.append("student_name = %s")
                update_values_student.append(student_name)
            if father_name:
                update_fields_student.append("father_name = %s")
                update_values_student.append(father_name)
            if mother_name:
                update_fields_student.append("mother_name = %s")
                update_values_student.append(mother_name)
            if dob:
                update_fields_student.append("dob = %s")
                update_values_student.append(dob)
            if gender:
                update_fields_student.append("gender = %s")
                update_values_student.append(gender)
            if religion:
                update_fields_student.append("religion = %s")
                update_values_student.append(religion)
            if category:
                update_fields_student.append("category = %s")
                update_values_student.append(category)
            if mobile:
                update_fields_student.append("mobile = %s")
                update_values_student.append(mobile)
            if single_counselling:
                update_fields_training.append("single_counselling = %s")
                update_values_training.append(single_counselling)
            if group_counselling:
                update_fields_training.append("group_counselling = %s")
                update_values_training.append(group_counselling)
            if other_trainings:
                update_fields_training.append("other_trainings = %s")
                update_values_training.append(other_trainings)
            if ojt:
                update_fields_training.append("ojt = %s")
                update_values_training.append(ojt)
            if assessment:
                update_fields_training.append("assessment = %s")
                update_fields_training.append("assessment_date=%s")
                update_values_training.append(assessment)
                update_values_training.append(datetime.today().date())
            if guest_lecture:
                update_fields_training.append("guest_lecture = %s")
                update_values_training.append(guest_lecture)
            if industrial_visit:
                update_fields_training.append("industrial_visit = %s")
                update_values_training.append(industrial_visit)
            if school_name:
                update_fields_training.append("school_enrollment = %s")
                update_values_training.append(school_name)
                update_fields_training.append("udsi = %s")
                update_values_training.append(udsi)               
            
            if account_number:
                update_fields_bank.append("account_number = %s")
                update_values_bank.append(account_number)

            if account_number:
                update_fields_bank.append("account_number = %s")
                update_values_bank.append(account_number) 

            if ifsc:
                update_fields_bank.append("ifsc = %s")
                update_values_bank.append(ifsc)                 
                
                
            
            # Only proceed if there are fields to update
            if not school_name in update_fields_training and udsi in update_fields_training:
                flash('UDSI code cannot be filled without filling Enrolled School section','error')
                return redirect(url_for('update_profile'))

            if school_name in update_fields_training and not udsi in update_fields_training:
                flash('Please make sure you fill the UDSI code of your Enrolled School too','error')
                return redirect(url_for('update_profile'))
            
                
            if update_fields_student:
                update_values_student.append(can_id)  # Add can_id for WHERE clause
                
                update_query = f"UPDATE students SET {', '.join(update_fields_student)} WHERE can_id = %s"
                cursor.execute(update_query, update_values_student)
                conn.commit()
                
            if update_fields_training:
                update_values_training.append(can_id)  # Add can_id for WHERE clause
                
                update_query = f"UPDATE student_training SET {', '.join(update_fields_training)} WHERE can_id = %s"
                cursor.execute(update_query, update_values_training)
                conn.commit() 

            if update_fields_bank:
                update_values_bank.append(can_id)  # Add can_id for WHERE clause
                
                update_query = f"UPDATE bank_details SET {', '.join(update_fields_bank)} WHERE can_id = %s"
                cursor.execute(update_query, update_values_bank)
                conn.commit()   
            else:
                flash("No changes detected. Please modify at least one field to update.", "info")
                return redirect(url_for('update_profile'))
            
                            # Success - clear form data from session and redirect
            session.pop('update_form_data', None)
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile_display'))
            
            
        except IntegrityError as e:
            error_msg = str(e).lower()
            if "mobile" in error_msg:
                flash("Mobile number already registered", "error")
            else:
                flash(f"Database integrity error: {str(e)}", "error")
            return redirect(url_for('update_profile'))
            
        except OperationalError as e:
            flash(f"Database operational error: {str(e)}", "error")
            return redirect(url_for('update_profile'))
            
        except ValueError as e:
            flash(f"Invalid input data: {str(e)}", "error")
            return redirect(url_for('update_profile'))
            
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "error")
            return redirect(url_for('update_profile'))
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # GET request - get form data from session and render template
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
        return redirect(url_for('login'))
    
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

# Complete admin_dashboard route:
@app.route('/admin_dashboard')
def admin_dashboard():
    # Get pagination and filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 25  # Records per page
    
    # Get filter parameters from request
    trade_filter = request.args.get('trade')
    gender_filter = request.args.get('gender')
    district_filter = request.args.get('district')
    center_filter = request.args.get('center')
    ojt_filter = request.args.get('ojt_status')
    school_filter = request.args.get('school')
    group_counselling_filter = request.args.get('group_counselling')
    single_counselling_filter = request.args.get('single_counselling')
    assessment_filter = request.args.get('assessment')
    industrial_visit_filter = request.args.get('industrial_visit')
    religion_filter = request.args.get('religion')
    
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
                                 trades=[],
                                 genders=[],
                                 districts=[],
                                 religions=[],
                                 schools=[],
                                 current_filters={})
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
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
        
        # Apply filters
        if trade_filter:
            query += " AND st.trade = %s"
            params.append(trade_filter)
        if gender_filter:
            query += " AND s.gender = %s"
            params.append(gender_filter)
        if district_filter:
            query += " AND s.district = %s"
            params.append(district_filter)
        if center_filter:
            query += " AND s.center = %s"
            params.append(center_filter)
        if ojt_filter:
            query += " AND st.ojt = %s"
            params.append(ojt_filter)
        if school_filter:
            query += " AND st.school_enrollment = %s"
            params.append(school_filter)
        if single_counselling_filter:
            query += " AND st.single_counselling = %s"
            params.append(single_counselling_filter)
        if group_counselling_filter:
            query += " AND st.group_counselling = %s"
            params.append(group_counselling_filter)
        if assessment_filter:
            query += " AND st.assessment = %s"
            params.append(assessment_filter)
        if industrial_visit_filter:
            query += " AND st.industrial_visit = %s"
            params.append(industrial_visit_filter)
        if religion_filter:
            query += " AND s.religion = %s"
            params.append(religion_filter)
        
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
        
        # Get unique values for filter dropdowns
        cursor.execute("SELECT DISTINCT trade FROM student_training WHERE trade IS NOT NULL ORDER BY trade")
        trades = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT gender FROM students WHERE gender IS NOT NULL ORDER BY gender")
        genders = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT district FROM students WHERE district IS NOT NULL ORDER BY district")
        districts = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT religion FROM students WHERE religion IS NOT NULL ORDER BY religion")
        religions = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT school_enrollment FROM student_training WHERE school_enrollment IS NOT NULL ORDER BY school_enrollment")
        schools = [row[0] for row in cursor.fetchall()]
        
        # Calculate pagination info
        total_pages = (total_records + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return render_template(
            'admin_dashboard.html',
            students=students,
            total_records=total_records,
            page=page,
            total_pages=total_pages,
            has_prev=has_prev,
            has_next=has_next,
            trades=trades,
            genders=genders,
            districts=districts,
            religions=religions,
            schools=schools,
            # Pass current filter values back to template
            current_filters={
                'trade': trade_filter,
                'gender': gender_filter,
                'district': district_filter,
                'center': center_filter,
                'ojt_status': ojt_filter,
                'school': school_filter,
                'single_counselling': single_counselling_filter,
                'group_counselling': group_counselling_filter,
                'assessment': assessment_filter,
                'industrial_visit': industrial_visit_filter,
                'religion': religion_filter
            }
        )
        
    except Exception as e:
        print("Dashboard error:", str(e))
        flash("An error occurred while loading dashboard", "error")
        return render_template("admin_dashboard.html", 
                             students=[], 
                             total_records=0,
                             page=1,
                             total_pages=1,
                             has_prev=False,
                             has_next=False,
                             trades=[],
                             genders=[],
                             districts=[],
                             religions=[],
                             schools=[],
                             current_filters={})
    
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")