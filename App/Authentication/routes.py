from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, session
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash
from flask_socketio import emit
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime

# Import other necessary modules and models
from App.models import User, Masyarakat, Petugas, Notification
from App.utils import confirm_token, generate_confirmation_token, send_password_reset_email
from App import db, login_manager, mail, limiter

import random, string, logging

auth = Blueprint('auth', __name__)

# At the top of your routes.py file
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))  # Ambil objek User langsung

def generate_username(email):
    """Generate a username from the email address."""
    username_base = email.split('@')[0]
    random_digits = ''.join(random.choice(string.digits) for _ in range(4))
    return f"{username_base}{random_digits}"

def send_confirmation_email(user_email):
    try:
        token = generate_confirmation_token(user_email)
        
        # Get the current domain
        if request:
            base_url = request.host_url.rstrip('/')
        else:
            # Fallback to a config value if outside request context
            base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
        
        # Construct the confirmation URL using the current domain
        confirm_url = f"{base_url}{url_for('auth.confirm_email', token=token)}"
        
        html = render_template('auth/activate.html', confirm_url=confirm_url)
        subject = "Silakan konfirmasi email anda"
        msg = Message(subject, recipients=[user_email], html=html)
        current_app.logger.info(f"Mencoba mengirim email ke {user_email}")
        current_app.logger.info(f"Confirmation URL: {confirm_url}")
        mail.send(msg)
        current_app.logger.info(f"Email berhasil dikirim ke {user_email}")
    except Exception as e:
        current_app.logger.error(f"Kesalahan pengiriman email: {str(e)}")
        raise

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("100 per minute")
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email']
        logger.info(f"Login attempt for email: {email}")
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
                if not user.is_confirmed:
                    flash('Harap konfirmasikan akun Anda sebelum login.', 'warning')
                    return redirect(url_for('auth.login', email=email))
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
@limiter.limit("3 per hour")
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    if request.method == 'POST':
        email = request.form['email_address']
        logger.info(f"Attempt to register with email: {email}")
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email sudah terdaftar. Silakan gunakan email lain.', category='danger')
            return render_template('auth/register.html', page='register')

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

                # Send confirmation email
                send_confirmation_email(email)

                # flash('A confirmation email has been sent to your email address. Please check your inbox.', 'info')
                flash('Email konfirmasi telah dikirimkan ke email anda. Silakan cek kotak masuk.', 'info')
                return redirect(url_for('auth.login'))

            except Exception as e:
                db.session.rollback()
                flash('Terjadi kesalahan saat membuat akun. Silahkan coba lagi.', category='danger')
                print(f"Error during registration: {e}")

    return render_template('auth/register.html', page='register')

@auth.route('/email_template')
def email_template():
    return render_template('auth/email_template.html', page='email_template')

@auth.route('/confirm/<token>')
def confirm_email(token):
    logger.info(f"Email confirmation attempt with token: {token[:10]}...")
    try:
        email = confirm_token(token)
    except:
        flash('Link konfirmasi tidak valid atau telah kedaluwarsa.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first_or_404()
    if user.is_confirmed:
        flash('Akun sudah dikonfirmasi. Silakan login.', 'success')
    else:
        user.is_confirmed = True
        user.confirmed_on = datetime.now()
        db.session.add(user)
        db.session.commit()

        # --- Send notification to Admin --- 
        admin = User.query.filter_by(user_type='admin').first()  # Get the admin user
        if admin:
            notification = Notification(
                recipient_id=admin.id,
                message=f"User {user.username} ({user.email}) has confirmed their account!"
            )
            db.session.add(notification)
            db.session.commit()

            # --- Emit SocketIO event to the admin  ---
            emit('new_user_confirmed', {'message': notification.message}, room=admin.id, namespace='/')
        flash('Anda telah mengonfirmasi akun Anda. Terima kasih!', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handles user request to reset forgotten password."""
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user)
            flash('Email untuk atur ulang kata sandi telah terkirim. Silahkan periksa kotak masuk anda.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Tidak ditemukan akun dengan email tersebut.', 'warning')
            return redirect(url_for('auth.forgot_password'))
    return render_template('auth/forgot_password.html')

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles password reset with the provided token."""
    user = User.verify_reset_password_token(token)
    if not user:
        flash('Token tidak valid atau sudah kadaluarsa', 'warning')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Konfirmasi kata sandi tidak cocok.', 'danger')
            return redirect(url_for('auth.reset_password', token=token)) 
        
        user.password_hash=generate_password_hash(password, method='pbkdf2')

        db.session.commit()
        flash('Kata sandi anda telah diperbarui! Silahkan masuk dengan kata sandi baru.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')

@auth.route('/resend')
@limiter.limit("3 per hour")
def resend_confirmation():
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    return render_template('auth/resend_confirmation.html')

@auth.route('/resend', methods=['POST'])
def resend_confirmation_post():
    email = request.form['email']
    user = User.query.filter_by(email=email).first()

    if user:
        if user.is_confirmed:
            flash('Akun sudah dikonfirmasi. Silakan login.', 'info')
        else:
            send_confirmation_email(user.email)
            flash('Email konfirmasi baru telah dikirim.', 'success')
    else:
        flash('Tidak ditemukan akun dengan alamat email tersebut.', 'danger')

    return redirect(url_for('auth.login'))

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

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email sudah terdaftar. Silakan gunakan email lain.', category='danger')
            return render_template('auth/officer_register.html', page='register')

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

                # Send confirmation email
                send_confirmation_email(email)

                # flash('A confirmation email has been sent to your email address. Please check your inbox.', 'info')
                flash('Email konfirmasi telah dikirimkan ke email anda. Silakan cek kotak masuk.', 'info')
                return redirect(url_for('auth.login'))

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