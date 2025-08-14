from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from datetime import datetime

# ---- LangChain & Chatbot ----
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
##from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from src.emotion import detect_emotion  # 👈 Import the emotion detector

from src.prompt import prompt
from src.summarizer import extract_text_from_pdf, summarize_report  # 👈 For summarization


# ---- Models ----
from models import db, User, Reminder,Appointment

# ---- Flask Setup ----
app = Flask(__name__)
app.secret_key = 'fj3#kDd9@XzL!vPQ2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ---- Flask-Login Setup ----
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---- Load .env ----
load_dotenv()
os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY")
##os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# ---- Chatbot Setup ----
embeddings = download_hugging_face_embeddings()
index_name = "medical-chatbot"
docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})
##chat_model = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash", temperature=0.5)
chat_model = ChatGroq(
    groq_api_key=os.environ["GROQ_API_KEY"],
    model_name="llama3-70b-8192",
    temperature=0.5
)
question_answer_chain = create_stuff_documents_chain(chat_model, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# ---- Routes ----
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = generate_password_hash(request.form['password'])

            phone = request.form.get('phone')
            address = request.form.get('address')
            dob = request.form.get('dob')
            disease = request.form.get('disease')
            caretaker_name = request.form.get('caretaker_name')
            caretaker_phone = request.form.get('caretaker_phone')

            if User.query.filter_by(email=email).first():
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))

            user = User(
                username=username,
                email=email,
                password=password,
                phone=phone,
                address=address,
                dob=datetime.strptime(dob, '%Y-%m-%d') if dob else None,
                disease=disease,
                caretaker_name=caretaker_name,
                caretaker_phone=caretaker_phone
            )

            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash('Something went wrong. Check form data.', 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', user=current_user, reminders=reminders)

@app.route('/chat')
@login_required
def chat_ui():
    return render_template('chat.html', user=current_user)

@app.route('/get', methods=['POST'])
@login_required
def chat():
    msg = request.form["msg"]

    # 1. Detect emotion
    emotion = detect_emotion(msg)

    # 2. Fetch medical answer from RAG
    response = rag_chain.invoke({"input": msg})
    medical_answer = response["answer"]

    # 3. Add empathy prefix
    emotion_prefixes = {
        "sadness": "I'm really sorry you're feeling this way. ",
        "joy": "That's great to hear! 😊 ",
        "fear": "I understand that this might be scary. ",
        "anger": "I hear your frustration. ",
        "neutral": "",
        "surprise": "Interesting! ",
        "disgust": "That sounds unpleasant. ",
        "love": "Sending positive energy your way. ❤️"
    }

    empathy = emotion_prefixes.get(emotion, "")
    final_response = empathy + medical_answer

    return str(final_response)


@app.route('/diet')
@login_required
def diet():
    return render_template('diet.html')


@app.route('/reminders/add', methods=['POST'])
@login_required
def add_reminder():
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    time = request.form['time']
    new_reminder = Reminder(
        title=title,
        description=description,
        date=datetime.strptime(date, '%Y-%m-%d').date(),
        time=datetime.strptime(time, '%H:%M').time(),
        user_id=current_user.id
    )
    db.session.add(new_reminder)
    db.session.commit()
    flash('Reminder added!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/reminder/delete/<int:id>', methods=['POST'])
@login_required
def delete_reminder(id):
    reminder = Reminder.query.get_or_404(id)
    if reminder.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(reminder)
    db.session.commit()
    flash('Reminder deleted.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reminder')
@login_required
def reminder_page():
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    return render_template('reminders.html', reminders=reminders)

@app.route('/summarize', methods=['GET', 'POST'])
@login_required
def summarize():
    if request.method == 'POST':
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        # Save uploaded file
        upload_path = os.path.join("uploads", file.filename)
        file.save(upload_path)

        try:
            # Extract text and summarize
            text = extract_text_from_pdf(upload_path)
            summary = summarize_report(text)
        except Exception as e:
            summary = f"⚠️ Error processing file: {e}"

        return render_template("summary.html", summary=summary, user=current_user)

    return render_template("summarize_upload.html", user=current_user)

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    if request.method == 'POST':
        doctor_name = request.form.get('doctor_name')
        date_str = request.form.get('date')
        time_str = request.form.get('time')

        if not doctor_name or not date_str or not time_str:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('appointments'))

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_obj = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('appointments'))

        new_appointment = Appointment(
            doctor_name=doctor_name,
            date=date_obj,
            time=time_obj,
            user_id=current_user.id
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Appointment added successfully!', 'success')
        return redirect(url_for('appointments'))

    # GET: show user's appointments
    user_appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
    return render_template('appointment.html', appointments=user_appointments)


# Delete appointment route
@app.route('/appointments/delete/<int:id>', methods=['POST'])
@login_required
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.user_id != current_user.id:
        abort(403)  # Forbidden if user tries to delete others' appointments
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment deleted successfully.', 'info')
    return redirect(url_for('appointments'))



# ---- Run App ----
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8080, debug=True)
