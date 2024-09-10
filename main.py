import os
from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash, send_file
import matplotlib.pyplot as plt 
import matplotlib
matplotlib.use('Agg')
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from PyPDF2 import PdfReader
from bson.objectid import ObjectId
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from requests import HTTPError
import io

from secret_key import openapi_key, MONGO_URI
os.environ['OPENAI_API_KEY'] = openapi_key

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Replace with your secret key

conn = MongoClient(MONGO_URI)
db = conn['AI-Recruiter']

applicants_login = db['applicants_login']
recruiters_login = db['recruiters_login']
jobs = db['jobs']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def recruiter_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'recruiter':
            flash("You do not have permission to access this page.", "error")
        return f(*args, **kwargs)
    return decorated_function

def applicant_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'applicant':
            flash("You do not have permission to access this page.", "error")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    session.clear()
    return render_template('home.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    role = request.form.get('role')
    action = request.form.get('action')
    
    if action == 'login':
        return redirect(url_for('login', role=role))
    elif action == 'signup':
        return redirect(url_for('signup', role=role))

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    next_url = request.args.get('next')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if role == 'applicant':
            user = applicants_login.find_one({'email': email})
        elif role == 'recruiter':
            user = recruiters_login.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            session['role'] = role
            if next_url:
                return redirect(next_url)
            if role == 'recruiter':
                return redirect(url_for('recruiter_dashboard'))
            elif role == 'applicant':
                return redirect(url_for('applicant_dashboard'))
        else:
            error = "Invalid email or password. Please try again."
            return render_template('login.html', role=role, error=error, next=next_url)
    return render_template('login.html', role=role, next=next_url)


@app.route('/signup/<role>', methods=['GET', 'POST'])
def signup(role):
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            error = "Passwords don't match. Please try again."
            return render_template('signup.html', role=role, error=error)
        else:
            hashed_password = generate_password_hash(password)
            new_user = {'email': email, 'password': hashed_password}
            if role == 'applicant':
                existing_user = applicants_login.find_one({'email': email})
                if existing_user:
                    error = "Account with this email ID already exists. Try to log in."
                    return render_template('signup.html', role=role, error=error)
                applicants_login.insert_one(new_user)
            elif role == 'recruiter':
                existing_user = recruiters_login.find_one({'email': email})
                if existing_user:
                    error = "Account with this email ID already exists. Try to log in."
                    return render_template('signup.html', role=role, error=error)
                recruiters_login.insert_one(new_user)
            return redirect(url_for('home'))
    return render_template('signup.html', role=role)

@app.route('/recruiter_dashboard', methods=['GET', 'POST'])
@login_required
@recruiter_required
def recruiter_dashboard():
    # Fetch all jobs created by the logged-in recruiter
    email = session['user']
    existing_jobs = jobs.find({'email': email})
    return render_template('recruiter_dashboard.html', jobs=existing_jobs)

@app.route('/recruiter_dashboard_create', methods=['GET', 'POST'])
@login_required
@recruiter_required
def recruiter_dashboard_create():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        position = request.form.get('position')
        primary_skills = request.form.get('primary_skills')
        secondary_skills = request.form.get('secondary_skills')
        job_description_file = request.files['pdf']
        jobDescription = " "
        pdf_reader = PdfReader(job_description_file)
        for page in pdf_reader.pages:
            jobDescription += page.extract_text() 
        
        collection_name = f"{company_name}{position}{datetime.now().strftime('%Y%m%d')}"
        # Check if the collection already exists
        if collection_name in db.list_collection_names():
            flash("Job already exists", "error")
            return redirect(url_for('recruiter_dashboard_create'))
        db[collection_name]
        
        new_job = {'email': session['user'], 'job_collection_name': collection_name, 'status': 'open', 'compiled': 'no', 'company_name': company_name, 'position': position, 'job_description': jobDescription, 'primary_skills': primary_skills, 'secondary_skills': secondary_skills}
        jobs.insert_one(new_job)

        flash("Job created successfully", "success")
        return redirect(url_for('recruiter_dashboard_create'))
    return render_template('recruiter_dashboard_create.html')

@app.route('/applicant_dashboard', methods=['GET'])
@login_required
@applicant_required
def applicant_dashboard():
    # Fetch all open jobs
    open_jobs = jobs.find({'status': 'open'})
    return render_template('applicant_dashboard.html', jobs=open_jobs)

@app.route('/apply_job/<job_id>', methods=['GET', 'POST'])
@login_required
@applicant_required
def apply_job(job_id):
    job = jobs.find_one({'_id': ObjectId(job_id)})
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        resume_file = request.files['resume']
        
        resume_extracted_info, skills = extract_resume_info(resume_file)
        
        application = {'job_id': job_id, 'status':'Processing', 'name': name, 'email': email, 'resume_content': resume_extracted_info, 'skills': skills, 'application_date': datetime.now()}
        # Save application to the job-specific collection
        db[job['job_collection_name']].insert_one(application)
        
        flash("Application submitted successfully", "success")
        # return redirect(url_for('applicant_dashboard'))
    
    return render_template('apply_job.html', job=job)

def extract_resume_info(resume_path):
    resumeText = " "
    pdf_reader = PdfReader(resume_path)
    for page in pdf_reader.pages:
        resumeText += page.extract_text() 
    
    llm = ChatOpenAI(temperature=0.2)
    
    with get_openai_callback() as cb:
        prompt = f"Extract the following information from the resume given below: Name, Email, Contact Info,  Website links, Education, Skills, Experience, Projects, Additional Info. Resume : {resumeText}"
        
        messages = [
            ("system", " Answer the following question with the given information. If you do not know the answer, say null"),
            ("human", prompt)]
        
        resumeResponse = llm.invoke(messages)
        print(cb)
    print(resumeResponse.content)
    
    parts = resumeResponse.content.split('\n')
    print(parts)
    
    if 'Skills:' in parts:
        start_index = parts.index('Skills:')
        if 'Experience:' in parts:
            stop_index = parts.index('Experience:')
            sublist = parts[start_index:stop_index]
        else:
            sublist = parts[start_index:]
        print("SUBLIST:", sublist)
        
        skills = ', '.join(sublist)
    else:
        # If "Skills:" not found, search for a substring containing "Skills"
        sublist = [element for element in parts if 'Skills' in element]
        if sublist:
            skills = ', '.join(sublist)
        else:
            skills = ''
    print(skills)

    return resumeResponse.content, skills

@app.route('/view_my_applications', methods=['GET'])
@login_required
@applicant_required
def view_my_applications():
    email = session['user']
    all_jobs = jobs.find()  # Find all jobs to match job collections
    applications = []
    for job in all_jobs:
        job_applications = db[job['job_collection_name']].find({'email': email})
        for application in job_applications:
            application_details = {
                'company_name': job['company_name'],
                'position': job['position'],
                'application_date': application['application_date'],
                'status': application.get('status', 'N/A')  
            }
            applications.append(application_details)
    return render_template('view_my_applications.html', applications=applications)

@app.route('/compile_applications/<job_id>', methods=['POST'])
@recruiter_required
def compile_applications(job_id):
    if request.method == 'POST':
        job = jobs.find_one({'_id': ObjectId(job_id)})
        collection_name = job['job_collection_name']
        job_description = job['job_description']
        primary_skills = job['primary_skills']
        secondary_skills = job['secondary_skills']
        
        if job['status'] == 'open':
            flash("Applications for this job cannot be compiled as the job status is open", "error")
            return redirect(url_for('view_applications', job_id=job_id)) 
        
        cleaned_job_description = job_description.replace('\n', ' ')
        print(cleaned_job_description)
        
        applications = db[collection_name].find()
        
        application_count = db[collection_name].count_documents({})
        if application_count == 0:
            flash("There are no applications to compile for this job", "error")
            return redirect(url_for('view_applications', job_id=job_id)) 
        
        for application in applications:
            resume_content = application.get('resume_content', '')
            resume_skills = application.get('skills', '')
            
            jobDescriptionScore = jobDescription_matching(resume_content, cleaned_job_description)
            primarySkillScore, secondarySkillScore = skills_matching(resume_skills, primary_skills, secondary_skills)
        
            total_score = float(primarySkillScore) + float(secondarySkillScore) + float(jobDescriptionScore)
        
            db[collection_name].update_one({'_id': application['_id']}, {'$set': {'JDscore': jobDescriptionScore, 'primarySkillScore': primarySkillScore, 'secondarySkillScore': secondarySkillScore, 'total_score': total_score}})
            
        jobs.update_one({'_id': ObjectId(job_id)}, {'$set': {'compiled': 'yes'}})
    
    flash("Applications for this job have been compiled", "success")
    return redirect(url_for('view_applications', job_id=job_id))


def jobDescription_matching(resume, job_description):
    llm = ChatOpenAI(temperature=0.2)
    prompt = f"Give the job fit as a percentage for the job description : {job_description} and the given resume : {resume}."
    messages = [
    ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 40"),
    ("human", prompt)]
    jobDescription_matching_score = llm.invoke(messages)
    print("Job Description Matching Score :" , jobDescription_matching_score.content)
    return jobDescription_matching_score.content

def skills_matching(resume_skills, primary_skills, secondary_skills):
    resume_skills_list = resume_skills.split(',')
    llm = ChatOpenAI(temperature=0.2)
    with get_openai_callback() as cb:
        # Calculate similarity scores for primary skills
        prompt1 = f"Find the intersection between set 1 : {', '.join(resume_skills_list)} and set 2 : {primary_skills}. Give me a percentage as (intersection/number of items in set 2)*100."  
        messages = [
            ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
            ("human", prompt1)]
        primary_similarity_scores = llm.invoke(messages)
        print("Primary Skills Match :" , primary_similarity_scores.content)
        
        # Calculate similarity scores for secondary skills
        prompt2 = f"Find the intersection between set 1 : {', '.join(resume_skills_list)} and set 2 : {secondary_skills}. Give me a percentage as (intersection/number of items in set 2)*100."  
        messages = [
            ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
            ("human", prompt2)]
        secondary_similarity_scores = llm.invoke(messages)
        print("Secondary Skills Match :" , secondary_similarity_scores.content) 
        
        print(cb)
    
    return primary_similarity_scores.content, secondary_similarity_scores.content

@app.route('/view_applications/<job_id>', methods=['GET', 'POST'])
@login_required
@recruiter_required
def view_applications(job_id):
    job = jobs.find_one({'_id': ObjectId(job_id)})
    applications_cursor = db[job['job_collection_name']].find().sort('total_score', -1)
    applications = list(applications_cursor)  # Convert cursor to list

    if request.method == 'POST':
        if 'send_emails_button' in request.form:
            send_emails_to_top_candidates(job_id)
            flash("Emails sent to top 5 candidates.", "success")
            return redirect(url_for('view_applications', job_id=job_id))

    return render_template('view_applications.html', job=job, applications=applications)

@app.route('/send_emails_to_top_candidates/<job_id>', methods=['POST'])
@login_required
@recruiter_required
def send_emails_to_top_candidates(job_id):
    job = jobs.find_one({'_id': ObjectId(job_id)})
    applications = list(db[job['job_collection_name']].find().sort('total_score', -1).limit(5))
    for application in applications:
        email = application['email']
        subject = f"Application for {job['position']} at {job['company_name']}"
        body = f"Dear {application['name']},\n\nWe are pleased to inform you that you have been shortlisted for the position of {job['position']} at {job['company_name']}.\n\nBest regards,\n{job['company_name']} Recruitment Team"
        send_email(email, subject, body)
    
    return render_template('view_applications.html', job=job, applications=applications)

def send_email(email, subject, body):
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)

    message = MIMEText(body)
    message['to'] = email
    message['subject'] = subject
    create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

    try:
        message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(F'sent message to {message} Message Id: {message["id"]}')
    except HTTPError as error:
        print(F'An error occurred: {error}')
        message = None


@app.route('/close_applications/<job_id>', methods=['POST'])
@login_required
@recruiter_required
def close_applications(job_id):
    job = jobs.find_one({'_id': ObjectId(job_id)})
    if job['status'] == 'closed':
        flash("Applications for this job are already closed", "error")
        return redirect(url_for('recruiter_dashboard'))
    # Update the job status to "closed"
    jobs.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'closed'}})
    flash("Applications for this job have been closed", "success")
    return redirect(url_for('view_applications', job_id=job_id)) 

@app.route('/view_graph/<job_id>', methods=['POST'])
@login_required
@recruiter_required
def view_graph(job_id):
    job = jobs.find_one({'_id': ObjectId(job_id)})
    applications = db[job['job_collection_name']].find()

    names = []
    scores = []

    for application in applications:
        names.append(application['name'])
        scores.append(application['total_score'])

    # Check if there are no applications
    if not names:
        return render_template_string('''
            <script>
                alert('No applications found for this job. Unable to generate graph.');
                window.history.back();  // Go back to the previous page
            </script>
        ''')

    # Create figure and axis objects with non-interactive backend
    fig, ax = plt.subplots(figsize=(8, len(names) * 0.5))
    ax.barh(names, scores, color='green')
    ax.set_xlabel('Total Score')
    ax.set_ylabel('Candidate Names')
    ax.set_title('Candidate Scores')

    # Automatically adjust subplot parameters to give padding
    plt.tight_layout()

    # Save to BytesIO object
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    
    # Clear the current figure
    plt.close(fig)

    return send_file(img, mimetype='image/png')

@app.route('/interview_login', methods=['GET', 'POST'])
@login_required
@applicant_required
def interview_login():
    if 'user' not in session:
        return redirect(url_for('login', role='applicant', next=url_for('interview_login')))
    if request.method == 'POST':
        code = request.form.get('code')
        job = jobs.find_one({'code': code})
        if job:
            collection_name = job['job_collection_name']
            job_id = job['_id']
            user_collection = db[collection_name]
            user_details = user_collection.find_one({'email': session['user']})
            resume = user_details['resume_content']
            job_description = job['job_description']
            return redirect(url_for('interview', job_id = job_id))
        else:
            flash("Invalid job code.", "error")
            return redirect(url_for('applicant_dashboard'))
    return render_template('interview_login.html')

@app.route('/interview/<job_id>', methods=['GET', 'POST'])
@login_required
@applicant_required  
def interview(job_id):
    resume = request.args.get('resume')
    job_description = request.args.get('job_description')
    job = jobs.find_one({'_id': ObjectId(job_id)})
    
    if request.method == 'POST':
        user_message = request.form['user_message']
        bot_response = interview_questions(user_message, resume, job_description)
        
        print(user_message)
        print(bot_response)
        
        if bot_response.startswith("Thank you"):
            interview_score = interview_scoring()
            collection_name = job['job_collection_name']
            user_collection = db[collection_name]
            user_collection.update_one({'email': session['user']}, {'$set': {'interview_score': interview_score}})
            session.clear()
            pass
        
        return {'bot_response': bot_response}
    
    return render_template('interview.html', job_id = job_id)
         
def interview_questions(user_message, resume_content, jd_content):
    if 'conversation_history' not in session or 'question_count' not in session:
        session['conversation_history'] = []
        session['question_count'] = 0
    
    conversation_history = session['conversation_history']
    question_count = session['question_count']
    print(session['conversation_history'])
    print(session['question_count'], question_count)
    
    llm = ChatOpenAI(temperature=0.2)
    
    if not conversation_history:
        if user_message.lower() == 'hello':
            default_question = "Let's start the interview. Please tell me about your experience."
            conversation_history.append(("bot", default_question))
            session['conversation_history'] = conversation_history
            return default_question
        else:
            return "Type 'hello' to start the interview."
    else:
        conversation_history.append(("human", user_message))
        session['conversation_history'] = conversation_history

        if question_count >= 4:
            return "Thank you for participating in the interview. You will receive further communication soon."

        prompt = f"You are an interviewer tasked with assessing a candidate. Based on the conversation history provided along with the resume and job description given below, ask the candidate a question. Ensure it's unique. Based on the conversation history, make sure the question is not of the same topic as covered before. Only one question should be asked at a time. Resume : {resume_content}\n Job Description : {jd_content}\n Chat History : {conversation_history}"
        
        messages = [
            ("system", " Act as an interviewer and complete the task given. Do not ask questions on the same topics or repeat similar questions as covered in conversation history. Return only the final generated interview question and nothing else."),
            ("human", prompt)
        ]
        
        with get_openai_callback() as cb:
            question = llm.invoke(messages)
            if not question:
                return "An error occurred while generating the question. Please try again."
        
        conversation_history.append(("bot", question.content))
        session['conversation_history'] = conversation_history
        session['question_count'] = question_count + 1
        session.modified = True
        
        return question.content

def interview_scoring() :
    llm = ChatOpenAI(temperature=0.2)
    conversation_history = session['conversation_history']
    with get_openai_callback() as cb:
        
        prompt = f"You are an interviewer tasked with assessing a candidate. Based on the conversation history provided, assess the candidate's responses on the basis of communication, relevant experience and problem solving skills. Score every answer out of 10. Return (score/number of questions)*100 \n Chat History : {conversation_history}"
            
        messages = [
                ("system", "Answer the following question with a percentage as an answer. Do not give any further explanations. Output the percentage without the % sign. If you do not know the answer, say 0"),
                ("human", prompt)]
    
        interview_score = llm.invoke(messages)
        print("Interview Score :" , interview_score.content)
    print(cb)
    return interview_score.content

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    session.pop('role', None)
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(port=8000, debug=True)