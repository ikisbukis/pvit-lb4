from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'neurostep_super_secret_key_2026'

# Ініціалізація БД
def init_db():
    conn = sqlite3.connect('neurostep.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY,
                 email TEXT UNIQUE,
                 password TEXT,
                 role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS profiles (
                 user_id INTEGER,
                 name TEXT,
                 age INTEGER,
                 injury TEXT,
                 ptsd_status TEXT,
                 goals TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                 id INTEGER PRIMARY KEY,
                 user_id INTEGER,
                 scenario TEXT,
                 completed_tasks INTEGER,
                 total_tasks INTEGER,
                 completion REAL,
                 date TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

# ====================== АВТЕНТИФІКАЦІЯ ======================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # patient / specialist / admin
        
        conn = sqlite3.connect('neurostep.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                     (email, password, role))
            conn.commit()
            user_id = c.lastrowid
            if role == 'patient':
                c.execute("INSERT INTO profiles (user_id, name) VALUES (?, ?)", (user_id, email.split('@')[0]))
                conn.commit()
            flash('Реєстрація успішна!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Такий email вже існує!', 'danger')
        conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('neurostep.db')
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['role'] = user[1]
            flash('Вхід успішний!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Невірні дані!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ====================== ДАШБОРД ======================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    role = session['role']
    
    conn = sqlite3.connect('neurostep.db')
    c = conn.cursor()
    
    if role == 'patient':
        c.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))
        profile = c.fetchone()
        c.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY date DESC", (user_id,))
        sessions = c.fetchall()
        return render_template('patient_dashboard.html', profile=profile, sessions=sessions)
    
    elif role == 'specialist':
        c.execute("SELECT * FROM profiles")
        patients = c.fetchall()
        return render_template('specialist_dashboard.html', patients=patients)
    
    elif role == 'admin':
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        return render_template('admin_dashboard.html', users=users)

# ====================== ПРОФІЛЬ ПАЦІЄНТА ======================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('neurostep.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        injury = request.form['injury']
        ptsd = request.form['ptsd']
        goals = request.form['goals']
        c.execute("""UPDATE profiles SET name=?, age=?, injury=?, ptsd_status=?, goals=?
                     WHERE user_id=?""", (name, age, injury, ptsd, goals, user_id))
        conn.commit()
        flash('Профіль оновлено!', 'success')
    
    c.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))
    profile = c.fetchone()
    conn.close()
    return render_template('profile.html', profile=profile)

# ====================== VR СЕСІЯ (СИМУЛЯЦІЯ) ======================
@app.route('/vr_session', methods=['GET', 'POST'])
def vr_session():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    scenario = request.args.get('scenario', 'physical')
    
    if request.method == 'POST':
        completed = int(request.form['completed_tasks'])
        total = int(request.form['total_tasks'])
        completion = round((completed / total) * 100, 2)
        
        conn = sqlite3.connect('neurostep.db')
        c = conn.cursor()
        c.execute("""INSERT INTO sessions (user_id, scenario, completed_tasks, total_tasks, completion, date)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (user_id, scenario, completed, total, completion, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        
        flash(f'Сесія завершена! Прогрес: {completion}%', 'success')
        return redirect(url_for('dashboard'))
    
    # Симуляція VR-сценарію
    if scenario == 'physical':
        title = "Фізична реабілітація: Підйом руки"
        tasks = 5
        instruction = "Виконайте 5 повторів підйому руки (натискайте кнопку після кожного)"
    else:
        title = "Психологічна реабілітація: Спокійний ліс"
        tasks = 4
        instruction = "Пройдіть 4 етапи релаксації (натискайте кнопку)"
    
    return render_template('vr_session.html', title=title, tasks=tasks, instruction=instruction, scenario=scenario)

# ====================== СПЕЦІАЛІСТ — ПРИЗНАЧЕННЯ ПРОГРАМИ ======================
@app.route('/assign_program/<int:patient_id>', methods=['GET', 'POST'])
def assign_program(patient_id):
    if 'user_id' not in session or session['role'] != 'specialist':
        return redirect(url_for('dashboard'))
    # Тут можна додати логіку призначення, але для MVP достатньо заглушки
    flash('Програму призначено пацієнту!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)