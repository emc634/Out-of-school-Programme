from flask import Flask,render_template

app=Flask(__name__)

@app.route('/')
def index():
    return render_template("front.html")

@app.route('/student_signup')
def student_signup():
    
    return render_template('student_signup.html')

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')



if __name__ == '__main__':
    app.run(debug=True,port=5000,host="0.0.0.0")