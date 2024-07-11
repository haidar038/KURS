from flask import Blueprint, render_template, send_from_directory, request, redirect, flash, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
from flask_login import current_user, login_required
from babel.dates import format_datetime
# Import other necessary modules and models
from App.models import TPS, Artikel, Laporan, Petugas, User
from App import db

import pytz, os, json

officer = Blueprint('officer', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

def picture_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

def format_tanggal_locale(tanggal, locale='en'):
    # Dapatkan locale dari request atau gunakan default 'en'
    locale = request.accept_languages.best_match(['id', 'en']) or locale

    # Dapatkan timezone menggunakan pytz
    timezone = pytz.timezone('Asia/Jayapura')

    # Format tanggal berdasarkan locale
    formatted_date = format_datetime(
        tanggal,
        "EEEE, dd-MM-YYYY (HH:mm)",
        locale=locale,
        tzinfo=timezone
    )

    # Tambahkan informasi zona waktu WIT
    return f"{formatted_date} WIT"

@officer.route('/officer_dashboard')
@login_required
def index():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    # Get data for chart
    new_reports = Laporan.query.filter_by(status='1').count()
    on_process_reports = Laporan.query.filter_by(status='2').count()
    finished_reports = Laporan.query.filter_by(status='3').count()

    laporan_selesai = (
        Laporan.query.filter_by(status='3')
        .group_by(func.date(Laporan.tanggal_laporan))
        .order_by(func.date(Laporan.tanggal_laporan))
        .values(func.date(Laporan.tanggal_laporan), func.count(Laporan.id))
    )
    
    laporan_per_hari = {}
    for tanggal, jumlah in laporan_selesai:
        tanggal_str = tanggal.strftime('%Y-%m-%d')
        laporan_per_hari[tanggal_str] = jumlah

    tps = TPS.query.all()
    artikel = Artikel.query.all()

    nama_tps = [namaTPS.nama for namaTPS in tps]
    lat_tps = [latTPS.latitude for latTPS in tps]
    long_tps = [longTPS.longitude for longTPS in tps]

    return render_template(
        'officer_page/index.html',
        new_reports=new_reports,
        on_process_reports=on_process_reports,
        finished_reports=finished_reports,
        laporan_per_hari=laporan_per_hari,
        nama_tps=json.dumps(nama_tps), 
        lat_tps=json.dumps(lat_tps), 
        long_tps=json.dumps(long_tps), 
        tps=tps, 
        artikel=artikel, 
        page='officer_home'
    )

@officer.route('/officer_dashboard/daftar_laporan')
@login_required
def reports_list():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    data_tps = TPS.query.all()
    page = request.args.get('page', 1, type=int)
    per_page = 8
    data_laporan = Laporan.query.filter(Laporan.status.in_(['1', '2'])).paginate(page=page, per_page=per_page)

    foto_laporan = Laporan.query.all()

    for laporan in data_laporan.items:
        laporan.tanggal_laporan = format_tanggal_locale(laporan.tanggal_laporan)
        # Mengambil data TPS jika tps_id ada
        if laporan.tps_id: 
            laporan.tps = TPS.query.get(laporan.tps_id) 

    return render_template('officer_page/laporan.html', foto_laporan=foto_laporan, data_tps=data_tps, data_laporan=data_laporan, page=page, per_page=per_page, page_name='reports')

@officer.route('/report_picture/<string:id>')
def report_picture(id):
    """Mengirim foto profil ke halaman web atau gambar default jika tidak ada."""
    foto_sampah = Laporan.query.get_or_404(id)
    if foto_sampah.foto:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], foto_sampah.foto)
    else:
        return send_from_directory(current_app.config['STATIC_FOLDER'] + '/img/', 'trash_default.png')  

@officer.route('/officer_dashboard/daftar_laporan/konfirmasi/<string:id>', methods=['POST'])
@login_required
def confirm_report(id):
    laporan = Laporan.query.filter_by(id=id).first()
    
    # Ambil tps_id dari form data
    tps_id = request.form.get('pilihTPS')

    print(tps_id)
    if tps_id:
        laporan.tps_id = tps_id
        laporan.petugas_id = current_user.id
        laporan.status = '2'
        db.session.commit()
        flash('Laporan berhasil dikonfirmasi!', 'info')
    else:
        flash('Gagal mengonfirmasi laporan: TPS tidak valid!', 'error')
    
    return redirect(url_for('officer.reports_list'))

@officer.route('/officer_dashboard/daftar_laporan/selesai/<string:id>', methods=['POST'])
@login_required
def finish_report(id):
    laporan = Laporan.query.filter_by(id=id).first()
    petugas = Petugas.query.get(laporan.petugas_id) # Ambil objek Petugas dari laporan

    if petugas: 
        petugas.tambah_poin()  # Tambahkan 10 poin (default) 
    else: 
        # Tangani jika petugas tidak ditemukan
        flash('Petugas tidak ditemukan! Poin tidak ditambahkan', 'warning')
        print('Petugas tidak ditemukan! Poin tidak ditambahkan.') 

    laporan.status = '3'
    db.session.commit()
    flash('Laporan berhasil diselesaikan!', 'info')
    return redirect(url_for('officer.reports_list'))

@officer.route('/officer_dashboard/riwayat_laporan')
@login_required
def riwayat_laporan():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    page = request.args.get('page', 1, type=int)
    per_page = 8 
    data_laporan = Laporan.query.filter_by(status='3').paginate(page=page, per_page=per_page)

    for laporan in data_laporan.items:
        laporan.tanggal_laporan = format_tanggal_locale(laporan.tanggal_laporan)
        # Ambil data TPS berdasarkan tps_id 
        if laporan.tps_id:
            laporan.tps = TPS.query.get(laporan.tps_id)

    return render_template('officer_page/riwayat.html', data_laporan=data_laporan, page=page, per_page=per_page, page_name='riwayat')

# todo ================================ PROFILE SECTION ==============================
@officer.route('/officer_dashboard/officer_profile/<string:id>', methods=['GET', 'POST'])
@login_required
def profile(id):
    user_type = User.query.get_or_404(id)
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    return render_template('officer_page/profil.html', user=Petugas.query.filter_by(user_id=id).first(), page='profile')

@officer.route('/officer_dashboard/profile_picture/<string:id>')
def profile_picture(id):
    """Mengirim foto profil ke halaman web atau gambar default jika tidak ada."""
    user = Petugas.query.get_or_404(id)
    if user.foto_profil:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], user.foto_profil)
    else:
        return send_from_directory(current_app.config['STATIC_FOLDER'] + '/img/', 'profile/default.png')  
    
@officer.route('/officer_dashboard/update_profile_picture/<string:id>', methods=['POST'])
def update_profile_picture(id):
    user = Petugas.query.get_or_404(id)
    foto_profil = request.files.get('foto_profil')
    if foto_profil:
        foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], foto_profil.filename))
        user.foto_profil = foto_profil.filename
        db.session.commit()
        flash('Berhasil memperbarui foto profil', 'success')
        return redirect(url_for('officer.profile', id=id))

    if not foto_profil or not allowed_file(foto_profil.filename):
        flash('Foto profil tidak valid!', 'danger')
        return redirect(url_for('officer.profile', id=id))
    
    print(id)
    
    filename = secure_filename(foto_profil.filename)
    foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

    # update_profile_picture = Petugas(foto_profil=f'/static/img/profile/{filename}')
    
    user.foto_profil = f'/static/img/profile/{filename}'

    flash('Foto Profil Berhasil Diubah!', 'success')
    return redirect(url_for('officer.profile', id=id))

@officer.route('/officer_dashboard/profil/<string:id>/update_profil', methods=['POST'])
def update_profile(id):
    user = Petugas.query.filter_by(user_id=id).first()
    if request.method == 'POST':
        nama_petugas = request.form.get('nama_petugas')
        username = request.form.get('username')
        area_tugas = request.form.get('area_tugas')
        no_telepon = request.form.get('no_telepon')

        # Validasi (Anda dapat menambahkan validasi lain di sini jika diperlukan)

        user.nama_petugas = nama_petugas
        current_user.username = username
        user.area_tugas = area_tugas
        user.no_telepon = no_telepon
        db.session.commit()
        flash('Informasi pribadi Anda berhasil diubah!', 'success')
        return redirect(url_for('officer.profile', id=id))
        # return jsonify({'success': True, 'message': 'Informasi pribadi Anda berhasil diubah!'})

@officer.route('/officer_dashboard/profil/<string:id>/update_email', methods=['POST'])
def update_email(id):
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == current_user.email:
            return jsonify({'success': False, 'email_error': 'Email Anda masih sama, silakan perbarui ke email yang baru.'})
        
        existing_user = Petugas.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'email_error': 'Email sudah ada, silakan ubah email Anda!'})

        if not check_password_hash(current_user.password_hash, password):
            return jsonify({'success': False, 'password_error': 'Konfirmasi kata sandi tidak sesuai!'})

        current_user.email = email
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email anda berhasil diperbarui!'})

    return redirect(url_for('officer.profile', id=id))

@officer.route('/officer_dashboard/profil/<string:id>/update_password', methods=['GET', 'POST'])
def update_password(id):
    user = Petugas.query.get_or_404(id)

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if len(new_password) < 8:
            flash('Kata sandi minimal 8 karakter!', 'warning')
            return redirect(url_for('officer.profile', id=id))

        # Verifikasi old_password dengan hybrid_property 
        if not check_password_hash(current_user.password_hash, old_password):
            flash('Kata sandi lama tidak sesuai!', 'warning')
            return redirect(url_for('officer.profile', id=id))

        if new_password != confirm_password:
            flash('Konfirmasi kata sandi tidak sesuai!', 'warning')
            return redirect(url_for('officer.profile', id=id))

        # Update password di model User
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2')  # Gunakan hybrid_property 
        db.session.commit()
        
        # Refresh objek current_user 
        db.session.refresh(current_user)  # <--- Tambahkan baris ini

        flash('Kata sandi Anda berhasil diubah!', 'success')
        return redirect(url_for('officer.profile', id=id))

    return redirect(url_for('officer.profile', id=id))