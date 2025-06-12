from flask import Flask, render_template, request, flash, redirect, url_for,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

from functions import get_db_connection, get_student_data_db_connection,get_template_data,clear_session_data

app = Flask(__name__)
app.secret_key = 'bhuvnn'


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
            
        conn = get_db_connection("user.db")
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user is None or not check_password_hash(user['password_hash'], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("student_signin"))
            
        flash("Login successful!", "success")
        return redirect(url_for("student_profile"))
    
    return render_template("student_signup.html",email=session.get("email",""))  # Should be a different template


# Student data entry
@app.route('/update_profile', methods=["GET", "POST"])
def student_profile():
    if request.method == "POST":
        # Store form data in session (remove trailing commas that create tuples)
        session["firstName"] = request.form.get("firstName", "")
        session["lastName"] = request.form.get("lastName", "")
        session["fatherName"] = request.form.get("fatherName", "")
        session["motherName"] = request.form.get("motherName", "")
        session["dob"] = request.form.get("dob", "")
        session["gender"] = request.form.get("gender", "")
        session["religion"] = request.form.get("religion", "")
        session["category"] = request.form.get("category", "")
        session["aadhar"] = request.form.get("aadhar", "")
        session["mobile"] = request.form.get("mobile", "")
        # Fix: Use correct field name from HTML form
        session["canID"] = request.form.get("canId", "")  # HTML uses 'canId', not 'canID'
        session["center"] = request.form.get("center", "")
        session["subCenter"] = request.form.get("subCenter", "")
        session["trade"] = request.form.get("trade", "")
        session["accountNumber"] = request.form.get("accountNumber", "")
        session["accountHolder"] = request.form.get("accountHolder", "")
        session["ifsc"] = request.form.get("ifsc", "")
        session["ojt"] = request.form.get("ojt", "")
        session["guestLecture"] = request.form.get("guestLecture", "")
        session["industrialVisit"] = request.form.get("industrialVisit", "")
        session["assessment"] = request.form.get("assessment", "")
        
        # Debug: Print all form data to see what's being received
        print("=== FORM DATA DEBUG ===")
        for key, value in request.form.items():
            print(f"{key}: '{value}'")
        print("=== SESSION DATA DEBUG ===")
        for key in ["firstName", "lastName", "fatherName", "motherName", "dob", "gender",
                   "religion", "category", "aadhar", "mobile", "canID", "center", 
                   "subCenter", "trade", "accountNumber", "accountHolder", "ifsc", 
                   "ojt", "guestLecture", "industrialVisit", "assessment"]:
            print(f"{key}: '{session.get(key, 'NOT_FOUND')}'")
        print("=== END DEBUG ===")
        
        # Validate required fields
        required_fields = [
            session["firstName"], session["lastName"], session["fatherName"], 
            session["motherName"], session["dob"], session["gender"],
            session["religion"], session["category"], session["aadhar"], 
            session["mobile"], session["canID"], session["center"], 
            session["subCenter"], session["trade"], session["accountNumber"], 
            session["accountHolder"], session["ifsc"], session["ojt"], 
            session["guestLecture"], session["industrialVisit"], session["assessment"]
        ]
        
        # Check if any required field is empty or None
        empty_fields = []
        for i, field in enumerate(required_fields):
            field_names = ["firstName", "lastName", "fatherName", "motherName", "dob", "gender",
                          "religion", "category", "aadhar", "mobile", "canID", "center", 
                          "subCenter", "trade", "accountNumber", "accountHolder", "ifsc", 
                          "ojt", "guestLecture", "industrialVisit", "assessment"]
            if not field or not field.strip():
                empty_fields.append(field_names[i])
        
        if empty_fields:
            flash(f"Please fill in all required fields. Missing: {', '.join(empty_fields)}", "error")
            return render_template('student_profile.html', **get_template_data())

        # Validate specific fields
        if len(session["aadhar"]) != 12 or not session["aadhar"].isdigit():
            flash("Aadhar number must be exactly 12 digits", "error")
            return render_template('student_profile.html', **get_template_data())
        
        if len(session["mobile"]) != 10 or not session["mobile"].isdigit():
            flash("Mobile number must be exactly 10 digits", "error")
            return render_template('student_profile.html', **get_template_data())

        # Database operations
        conn = None
        try:
            conn = get_student_data_db_connection("student_data.db")
            conn.execute(
                """INSERT INTO students (
                first_name, last_name, father_name, mother_name, dob, 
                gender, religion, category, aadhar, mobile,
                can_id, center, subcenter, trade, account_number,
                account_holder, ifsc, ojt, guest_lecture, industrial_visit, assessment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session['firstName'], session['lastName'], session['fatherName'], 
                    session['motherName'], session['dob'], session['gender'], 
                    session['religion'], session['category'], session['aadhar'], 
                    session['mobile'], session['canID'], session['center'], 
                    session['subCenter'], session['trade'], session['accountNumber'],
                    session['accountHolder'], session['ifsc'], session['ojt'], 
                    session['guestLecture'], session['industrialVisit'], session['assessment']
                )
            )

            conn.commit()
            flash("Student data saved successfully!", "success")
            
            # Clear session data only after successful save
            clear_session_data()
            
            return redirect(url_for('student_profile'))

        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "aadhar" in error_msg:
                flash("Aadhar number already registered", "error")
            elif "can_id" in error_msg:
                flash("Candidate ID already exists", "error")
            else:
                flash(f"Database integrity error: {str(e)}", "error")
            
            return render_template('student_profile.html', **get_template_data())

        except Exception as e:
            flash(f"Error saving student data: {str(e)}", "error")
            return render_template('student_profile.html', **get_template_data())

        finally:
            if conn:
                conn.close()

    # For GET requests, return form with any existing session data
    return render_template('student_profile.html',first_name=session.get("first_name",""),
                                   last_name=session.get("last_name",""),
                                   mobile=session.get("mobile",""),
                                   email=session.get("email",""))



@app.route("/reset_password")
def reset_password():
    return render_template("reset_password.html")


@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")