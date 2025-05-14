from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'drivinschoolsecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drivingschool.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'instructor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student_lessons = db.relationship('Lesson', backref='student', lazy=True, 
                                     foreign_keys='Lesson.student_id')
    instructor_lessons = db.relationship('Lesson', backref='instructor', lazy=True,
                                        foreign_keys='Lesson.instructor_id')
    payments = db.relationship('Payment', backref='user', lazy=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    vehicle_class = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Payment
    payment = db.relationship('Payment', backref='lesson', lazy=True, uselist=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_class = db.Column(db.String(20), nullable=False)
    lessons_completed = db.Column(db.Integer, default=0)
    total_lessons = db.Column(db.Integer, default=10)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        admin_password = request.form.get('admin_password')
        
        # Check if instructor and admin password
        if user_type == 'instructor' and admin_password != 'MunasheRichard':
            flash('Invalid admin password for instructor registration')
            return redirect(url_for('register'))
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            user_type=user_type
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Check if user type matches
            if user.user_type != user_type:
                flash(f'This account is not registered as a {user_type}')
                return redirect(url_for('login'))
            
            # Set session
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            
            if user.user_type == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('instructor_dashboard'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    lessons = Lesson.query.filter_by(student_id=user_id).all()
    progress = Progress.query.filter_by(student_id=user_id).all()
    
    return render_template('student_dashboard.html', user=user, lessons=lessons, progress=progress)

@app.route('/student/schedule', methods=['GET', 'POST'])
def schedule_lesson():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        vehicle_class = request.form.get('vehicle_class')
        date_str = request.form.get('date')
        date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        
        new_lesson = Lesson(
            student_id=session['user_id'],
            vehicle_class=vehicle_class,
            date=date
        )
        
        db.session.add(new_lesson)
        db.session.commit()
        
        flash('Lesson scheduled successfully!')
        return redirect(url_for('student_dashboard'))
    
    return render_template('schedule_lesson.html')

@app.route('/student/payment/<int:lesson_id>', methods=['GET', 'POST'])
def make_payment(lesson_id):
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        amount = float(request.form.get('amount'))
        
        # In a real app, you would integrate with payment gateways here
        
        new_payment = Payment(
            user_id=session['user_id'],
            lesson_id=lesson_id,
            amount=amount,
            payment_method=payment_method,
            status='completed'  # Simulating successful payment
        )
        
        lesson.payment_status = 'paid'
        
        db.session.add(new_payment)
        db.session.commit()
        
        flash('Payment successful!')
        return redirect(url_for('student_dashboard'))
    
    return render_template('payment.html', lesson=lesson)

@app.route('/instructor/dashboard')
def instructor_dashboard():
    if 'user_id' not in session or session['user_type'] != 'instructor':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get all pending lessons
    pending_lessons = Lesson.query.filter_by(status='scheduled').all()
    
    # Get all students with their progress
    students_progress = db.session.query(User, Progress).join(
        Progress, User.id == Progress.student_id
    ).filter(User.user_type == 'student').all()
    
    return render_template('instructor_dashboard.html', 
                          user=user, 
                          pending_lessons=pending_lessons,
                          students_progress=students_progress)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)