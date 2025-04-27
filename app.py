from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from pymongo import MongoClient
from flask_uploads import UploadSet, configure_uploads, IMAGES
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['spidy_web_db']
users_collection = db['users']
resumes_collection = db['resumes']

# File upload setup
app.config['UPLOADED_RESUMES_DEST'] = 'uploads/resumes'  # Directory to store uploaded resumes
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
resumes = UploadSet('resumes', IMAGES)
configure_uploads(app, resumes)

# Ensure the uploads folder exists
if not os.path.exists(app.config['UPLOADED_RESUMES_DEST']):
    os.makedirs(app.config['UPLOADED_RESUMES_DEST'])

@app.route('/')
def home():
    if 'username' in session:
        if session.get('role') == 'jobseeker':
            return redirect(url_for('jobseeker_dashboard'))
        elif session.get('role') == 'employer':
            return redirect(url_for('employer_dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_data = {
            "username": request.form['name'],
            "email": request.form['email'],
            "password": request.form['password'],
            "role": request.form.get('role'),
            "profile_pic": "default_profile.png"  # default profile pic at registration
        }
        users_collection.insert_one(user_data)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email, "password": password})
        if user:
            session['username'] = user.get('username', user.get('name'))
            session['email'] = user['email']
            session['role'] = user['role']
            session['profile_pic'] = user.get('profile_pic', 'default_profile.png')  # Load profile picture

            if user['role'] == 'jobseeker':
                return redirect(url_for('jobseeker_dashboard'))
            elif user['role'] == 'employer':
                return redirect(url_for('employer_dashboard'))
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/resume', methods=['GET'])
def resume_form():
    if 'username' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))
    return render_template('resume_form.html')

import os

@app.route('/submit_resume', methods=['POST'])
def submit_resume():
    if 'username' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))

    # Handle file upload
    resume_file = request.files.get('resume_image')

    # Ensure the uploads folder exists
    upload_folder = os.path.join(os.getcwd(), 'uploads', 'resumes')  # Correct path
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)  # Create the folder if it doesn't exist

    # If a file is uploaded, save it
    if resume_file and allowed_file(resume_file.filename):
        filename = resumes.save(resume_file)  # Save the file using Flask-Uploads
        resume_url = os.path.join(upload_folder, filename)  # Full path to the saved file
        
        # Save the resume data to the database
        resume_data = {
            "username": session['username'],
            "email": session['email'],
            "school_10": request.form['school_10'],
            "board_10": request.form['board_10'],
            "marks_10": request.form['marks_10'],
            "school_12": request.form['school_12'],
            "board_12": request.form['board_12'],
            "marks_12": request.form['marks_12'],
            "experience": request.form['experience'],
            "projects": request.form['projects'],
            "skills": request.form['skills'],
            "resume_url": filename  # Store the filename only
        }

        resumes_collection.insert_one(resume_data)
        return redirect(url_for('jobseeker_dashboard'))

    return "Invalid file type or no file uploaded", 400

@app.route('/dashboard/jobseeker')
def jobseeker_dashboard():
    if 'username' not in session or session.get('role') != 'jobseeker':
        return redirect(url_for('login'))

    # Check if the user has uploaded a resume
    resume_data = resumes_collection.find_one({"username": session['username']})
    return render_template('jobseeker_dashboard.html', username=session['username'], profile_pic=session.get('profile_pic'), resume_data=resume_data)

@app.route('/dashboard/employer')
def employer_dashboard():
    if 'username' not in session or session.get('role') != 'employer':
        return redirect(url_for('login'))
    return render_template('employer_dashboard.html', username=session['username'])

@app.route('/resume_images/<filename>')
def view_resume_image(filename):
    return send_from_directory(app.config['UPLOADED_RESUMES_DEST'], filename)

@app.route('/view_resume/<filename>')
def view_resume(filename):
    return send_from_directory(app.config['UPLOADED_RESUMES_DEST'], filename)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    app.run(debug=True)
