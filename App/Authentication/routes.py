from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_user, logout_user

# Import other necessary modules and models
from App.models import User
from App import db, login_manager

import random, string

auth = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['account_type'] = 'user'
            login_user(user, remember=True)
            flash("Berhasil Masuk!", category='success')
            return redirect(url_for('views.index'))
        elif user is None:
            flash("Akun anda belum terdaftar, silakan daftar terlebih dahulu", category='warning')
            return redirect(url_for('auth.login', email=email))
        else:
            flash("Kata sandi salah, silakan coba lagi.", category='error')
            return redirect(url_for('auth.login', email=email))
    return render_template('auth/login.html', page='login')

# User Registration Route
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email_address']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Generate username
        username = generate_username(email)

        if len(password) < 8:
            flash('Kata sandi harus berisi 8 karakter atau lebih', category='error')
        elif confirm_password != password:
            flash('Kata sandi tidak cocok.', category='error')
        elif User.query.filter_by(email=email).first():
            flash('Email sudah digunakan, silakan buat yang lain.', category='error')
        else:
            try:
                regist_user = User(username=username, email=email, password_hash=generate_password_hash(password, method='pbkdf2'))

                db.session.add(regist_user)
                db.session.commit()

                flash('Akun berhasil dibuat! Silahkan cek email Anda untuk verifikasi.', category='success')
                return redirect(url_for('auth.login'))

            except Exception as e:
                db.session.rollback()
                flash('Terjadi kesalahan saat membuat akun. Silahkan coba lagi.', category='error')
                print(f"Error during registration: {e}")

    return render_template('auth/register.html', page='register')

def generate_username(email):
    """Generate a username from the email address."""
    username_base = email.split('@')[0]
    random_digits = ''.join(random.choice(string.digits) for _ in range(4))
    return f"{username_base}{random_digits}"
