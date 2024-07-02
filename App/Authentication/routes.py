from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_user, logout_user, login_required

# Import other necessary modules and models
from App.models import User, Masyarakat, Petugas
from App import db, login_manager

import random, string

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Cari user berdasarkan email di tabel Masyarakat dan Petugas
        user = User.query.join(Masyarakat, User.id == Masyarakat.user_id).filter_by(email=email).first()
        if not user:
            user = User.query.join(Petugas, User.id == Petugas.user_id).filter_by(email=email).first()

        if user:
            # Tentukan tipe user dan ambil objek yang sesuai
            if user.user_type == 'masyarakat':
                user_data = user.masyarakat
            elif user.user_type == 'petugas':
                user_data = user.petugas
            else:
                flash("Tipe akun tidak valid.", category='error')
                return redirect(url_for('auth.login', email=email))

            # Gunakan user_data.password_hash untuk verifikasi password
            if check_password_hash(user_data.password_hash, password): 
                session['account_type'] = user.user_type
                login_user(user_data, remember=True)
                flash("Berhasil Masuk!", category='success')
                return redirect(url_for('views.index'))
            else:
                flash("Kata sandi salah, silakan coba lagi.", category='error')
                return redirect(url_for('auth.login', email=email))
        else:
            flash("Akun anda belum terdaftar, silakan daftar terlebih dahulu", category='warning')
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
            flash('Kata sandi harus berisi 8 karakter atau lebih', category='danger')
        elif confirm_password != password:
            flash('Kata sandi tidak cocok.', category='danger')
        else:
            try:
                # Buat objek User dengan user_type 'masyarakat'
                new_user = User(user_type='masyarakat')
                db.session.add(new_user)
                db.session.flush()  # Simpan perubahan untuk mendapatkan user_id

                # Buat objek Masyarakat dengan user_id dari objek User yang baru dibuat
                new_user_data = Masyarakat(
                    user_id=new_user.id,  # Gunakan new_user.id
                    nama_lengkap='Nama Lengkap',  # Ganti dengan input nama lengkap
                    email=email,
                    username=username,
                    password_hash=generate_password_hash(password, method='pbkdf2'),
                    alamat='Alamat',  # Ganti dengan input alamat
                    no_telepon='Nomor Telepon'  # Ganti dengan input nomor telepon
                )

                db.session.add(new_user_data)
                db.session.commit()

                flash('Anda berhasil bergabung, silakan login', 'success')
                return redirect(url_for('auth.login', email=email))

            except Exception as e:
                db.session.rollback()
                flash('Terjadi kesalahan saat membuat akun. Silahkan coba lagi.', category='danger')
                print(f"Error during registration: {e}")

    return render_template('auth/register.html', page='register')

# Logout Route
@auth.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    # account_type = session.get('account_type')
    flash('Kamu telah logout!', 'warning')
    logout_user()
    session.clear()

    # if account_type == 'petugas':
    #     return redirect(url_for('auth.adminLogin'))
    # else:
    #     return redirect(url_for('auth.login'))
    return redirect(url_for('auth.login'))

def generate_username(email):
    """Generate a username from the email address."""
    username_base = email.split('@')[0]
    random_digits = ''.join(random.choice(string.digits) for _ in range(4))
    return f"{username_base}{random_digits}"
