from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_user, logout_user, login_required

# Import other necessary modules and models
from App.models import User, Masyarakat, Petugas, AppAdmin
from App import db, login_manager

import random, string

auth = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))  # Ambil objek User langsung

def generate_username(email):
    """Generate a username from the email address."""
    username_base = email.split('@')[0]
    random_digits = ''.join(random.choice(string.digits) for _ in range(4))
    return f"{username_base}{random_digits}"

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Cari user berdasarkan email di tabel Masyarakat dan Petugas
        user = User.query.filter_by(email=email).first()

        if user:
            # Tentukan tipe user dan ambil objek yang sesuai
            if user.user_type == 'masyarakat':
                user_data = user.masyarakat
            elif user.user_type == 'petugas':
                user_data = user.petugas
            elif user.user_type == 'admin':
                user_data = user.admin
            else:
                flash("Tipe akun tidak valid.", category='danger')
                return redirect(url_for('auth.login', email=email))

            # Gunakan user_data.password_hash untuk verifikasi password
            if check_password_hash(user.password_hash, password): 
                if user.user_type == 'masyarakat':
                    login_user(user_data, remember=True)
                    session['account_type'] = user.user_type 
                    flash("Berhasil Masuk!", category='success')
                    return redirect(url_for('views.index')) # Rute untuk masyarakat
                elif user.user_type == 'petugas':
                    login_user(user_data, remember=True)
                    session['account_type'] = user.user_type 
                    flash("Berhasil Masuk!", category='success')
                    return redirect(url_for('officer.index')) # Rute untuk petugas
                elif user.user_type == 'admin':
                    login_user(user_data, remember=True)
                    session['account_type'] = user.user_type 
                    flash("Berhasil Masuk!", category='success')
                    return redirect(url_for('app_admin.index')) # Rute untuk petugas
            else:
                flash("Kata sandi salah, silakan coba lagi.", category='danger')
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
                print(username)

                # Buat objek User dengan user_type 'masyarakat'
                new_user = User(
                    user_type='masyarakat',
                    email=email,
                    username=username,
                    password_hash=generate_password_hash(password, method='pbkdf2'))
                db.session.add(new_user)
                db.session.flush()  # Simpan perubahan untuk mendapatkan user_id

                # Buat objek Masyarakat dengan user_id dari objek User yang baru dibuat
                new_user_data = Masyarakat(
                    user_id=new_user.id,  # Gunakan new_user.id
                    nama_lengkap='Nama Lengkap',  # Ganti dengan input nama lengkap
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

#todo ================================== OFFICER SECTION ==================================

@auth.route('/register_officer', methods=['GET', 'POST'])
def register_officer():
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
                print(username)

                # Buat objek User dengan user_type 'masyarakat'
                new_user = User(
                    user_type='petugas',
                    email=email,
                    username=username,
                    password_hash=generate_password_hash(password, method='pbkdf2'))
                db.session.add(new_user)
                db.session.flush()  # Simpan perubahan untuk mendapatkan user_id

                # Buat objek Masyarakat dengan user_id dari objek User yang baru dibuat
                new_user_data = Petugas(
                    user_id=new_user.id,  # Gunakan new_user.id
                    nama_petugas='Nama Lengkap',  # Ganti dengan input nama lengkap
                    area_tugas='Area Tugas',  # Ganti dengan input alamat
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

    return render_template('auth/officer_register.html', page='register')

#todo ================================== ADMIN SECTION ==================================



#todo ================================== LOGOUT USER ==================================

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))