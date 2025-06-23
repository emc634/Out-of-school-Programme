from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import json
from psycopg2 import IntegrityError, OperationalError

from functions import get_db_connection

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
            'center':center
        }
        
        if not all([student_name, father_name, mother_name, gender, mobile,
                    can_id, religion, category, dob, district, trade, center, password, confirmation]):
            flash("Please fill in all required fields", "error")
            return redirect(url_for("student_signup"))
            
        if password != confirmation:
            flash("Password didn't match, Please Try again", "error")
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
                "INSERT INTO students (can_id, student_name, father_name, mother_name, mobile, religion, category, dob, district, center, trade, gender, password,total_days) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (can_id, student_name, father_name, mother_name, mobile, religion, category, dob, district, center, trade, gender, password_hash, course_days[trade])
            )
            conn.commit()
            
            flash("Account created successfully", "success")
            return redirect(url_for("student_profile"))
            
        except IntegrityError as e:
            # Handle duplicate primary key (can_id) or NOT NULL violations
            if 'duplicate key value violates unique constraint' in str(e):
                flash("Candidate ID already exists. Please use a different ID.", "error")
            elif 'null value in column' in str(e):
                flash("Some required fields are missing. Please fill all fields.", "error")
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
            
            cursor.execute(
                """UPDATE students SET aadhar=%s, account_number=%s, account_holder=%s, ifsc=%s
                   WHERE can_id=%s""",
                (aadhar, account_number, account_holder, ifsc, can_id)
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

@app.route("/profile_display")
def profile_display():
    can_id = session.get('can_id')
    if not can_id:
        return redirect(url_for('student_signin'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute('SELECT * FROM students WHERE can_id = %s', (can_id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("profile_display.html",student=student)


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
        ojt=request.form.get('ojt')
        guest_lecture=request.form.get('guestLecture')
        industrial_visit=request.form.get('industrialVisit')
        assessment=request.form.get('assessment')

        current_password = request.form.get("current_password")
        
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
            'assessment':assessment
        }
        
        # Validate required field - only current password is mandatory
        if not current_password:
            flash("Current password is required to update profile", "error")
            return redirect(url_for("update_profile"))
        
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
            
            # Verify current password
            if not check_password_hash(user['password'], current_password):
                flash("Current password is incorrect", "error")
                return redirect(url_for("update_profile"))
            
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
            update_fields = []
            update_values = []
            
            if student_name:
                update_fields.append("student_name = %s")
                update_values.append(student_name)
            if father_name:
                update_fields.append("father_name = %s")
                update_values.append(father_name)
            if mother_name:
                update_fields.append("mother_name = %s")
                update_values.append(mother_name)
            if dob:
                update_fields.append("dob = %s")
                update_values.append(dob)
            if gender:
                update_fields.append("gender = %s")
                update_values.append(gender)
            if religion:
                update_fields.append("religion = %s")
                update_values.append(religion)
            if category:
                update_fields.append("category = %s")
                update_values.append(category)
            if mobile:
                update_fields.append("mobile = %s")
                update_values.append(mobile)
            if ojt:
                update_fields.append("ojt = %s")
                update_values.append(ojt)
            if assessment:
                update_fields.append("assessment = %s")
                update_values.append(assessment)
            if guest_lecture:
                update_fields.append("guest_lecture = %s")
                update_values.append(guest_lecture)
            if industrial_visit:
                update_fields.append("industrial_visit = %s")
                update_values.append(industrial_visit)
                
                
            
            # Only proceed if there are fields to update
            if update_fields:
                update_values.append(can_id)  # Add can_id for WHERE clause
                
                update_query = f"UPDATE students SET {', '.join(update_fields)} WHERE can_id = %s"
                cursor.execute(update_query, update_values)
                conn.commit()
                
                # Success - clear form data from session and redirect
                session.pop('update_form_data', None)
                flash("Profile updated successfully!", "success")
                return redirect(url_for('profile_display'))
            else:
                flash("No changes detected. Please modify at least one field to update.", "info")
                return redirect(url_for('update_profile'))
            
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
                cursor.execute('SELECT attendance FROM students WHERE can_id = %s', (can_id,))
                result = cursor.fetchone()
                if not result:
                    flash("Student not found", "error")
                    return redirect(url_for('dashboard'))
                
                # Update attendance
                cursor.execute('UPDATE students SET attendance = %s WHERE can_id = %s', (attended_days, can_id))
                
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
            SELECT attendance, total_days, ojt, industrial_visit, assessment, guest_lecture 
            FROM students 
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
@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")