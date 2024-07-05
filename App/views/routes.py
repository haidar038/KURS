from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from flask_login import current_user, login_required, logout_user
from babel.dates import format_datetime
# Import other necessary modules and models
from App.models import TPS, Artikel, Laporan, Masyarakat
from App import db

import pytz, os, json

views = Blueprint('views', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

def picture_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

def save_profile_picture(file):
    """ Menyimpan gambar profil ke folder uploads.
    """
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return filename

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

@views.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@views.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')

@views.route('/')
@login_required
def index():
    user = Masyarakat.query.all()
    if current_user.user_id not in user:
        return redirect(url_for('officer.index'))
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    
    # logging.debug(f'User authenticated: {current_user.is_authenticated}')
    # logging.debug(f'Current user: {current_user}')

    tps = TPS.query.all()
    artikel = Artikel.query.all()

    nama_tps = [namaTPS.nama for namaTPS in tps]
    lat_tps = [latTPS.latitude for latTPS in tps]
    long_tps = [longTPS.longitude for longTPS in tps]

    return render_template('index.html', nama_tps=json.dumps(nama_tps), lat_tps=json.dumps(lat_tps), long_tps=json.dumps(long_tps), tps=tps, artikel=artikel, page='home')


@views.route('/wiki', methods=['GET'])
@login_required
def wiki():
    user = Masyarakat.query.all()
    if current_user.user_id not in user:
        return redirect(url_for('officer.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Jumlah artikel per halaman
    artikel_paginate = Artikel.query.paginate(page=page, per_page=per_page)

    return render_template('wiki.html', artikel_paginate=artikel_paginate, page='wiki')

@views.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    user = Masyarakat.query.all()
    if current_user.user_id not in user:
        return redirect(url_for('officer.index'))

    if request.method == 'POST':
        # Ambil data dari formulir
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        foto = request.files.get('foto')
        berat = request.form.get('berat')
        jenis_sampah = request.form.get('jenis_sampah')

        # Validasi data
        if not foto or not allowed_file(foto.filename):
            flash('File foto tidak valid!', 'danger')
            return redirect(url_for('views.reports'))

        # Simpan foto
        filename = secure_filename(foto.filename)
        foto.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        # Simpan data ke database (Model Laporan)
        laporan = Laporan(
            masyarakat_id=current_user.user_id,
            latitude=latitude,
            longitude=longitude,
            foto=f'/static/uploads/{filename}',
            berat=berat,
            jenis_sampah=jenis_sampah
        )
        db.session.add(laporan)
        db.session.commit()

        flash('Laporan berhasil dikirim!', 'success')
        return redirect(url_for('views.index'))

    return render_template('reports.html', page='reports')

@views.route('/reports/delete/<string:id>', methods=['GET', 'POST'])
@login_required
def delete_report(id):
    laporan = Laporan.query.filter_by(id=id).first()
    db.session.delete(laporan)
    db.session.commit()
    flash('Laporan berhasil dihapus!', 'warning')
    return redirect(url_for('views.history'))

@views.route('/riwayat', methods=['GET', 'POST'])
@login_required
def history():
    user = Masyarakat.query.all()
    if current_user.user_id not in user:
        return redirect(url_for('officer.index'))

    data_laporan = Laporan.query.filter_by(masyarakat_id=current_user.user_id).all()

    # Format tanggal untuk setiap laporan
    for laporan in data_laporan:
        laporan.tanggal_laporan = format_tanggal_locale(laporan.tanggal_laporan)

    return render_template('history.html', data_laporan=data_laporan, page='history')


# todo ====================== PROFILE SECTION ======================


@views.route('/profil/<string:id>', methods=['GET', 'POST'])
@login_required
def profil(id):
    user = Masyarakat.query.get_or_404(id)
    if current_user.user_id not in user:
        return redirect(url_for('officer.index'))
    return render_template('profile.html', user=user, page='profile')

@views.route('/profile_picture/<string:id>')
def profile_picture(id):
    """Mengirim foto profil ke halaman web atau gambar default jika tidak ada."""
    user = Masyarakat.query.get_or_404(id)
    if user.foto_profil:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], user.foto_profil)
    else:
        return send_from_directory(current_app.config['STATIC_FOLDER'] + '/img/', 'profile/default.png')  
    
@views.route('/update_profile_picture/<string:id>', methods=['POST'])
def update_profile_picture(id):
    user = Masyarakat.query.get_or_404(id)
    foto_profil = request.files.get('foto_profil')
    if foto_profil:
        foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], foto_profil.filename))
        user.foto_profil = foto_profil.filename
        db.session.commit()
        flash('Berhasil memperbarui foto profil', 'success')
        return redirect(url_for('views.profil', id=id))

    if not foto_profil or not allowed_file(foto_profil.filename):
        flash('Foto profil tidak valid!', 'danger')
        return redirect(url_for('views.profil', id=id))
    
    print(id)
    
    filename = secure_filename(foto_profil.filename)
    foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

    # update_profile_picture = Masyarakat(foto_profil=f'/static/img/profile/{filename}')
    
    user.foto_profil = f'/static/img/profile/{filename}'

    flash('Foto Profil Berhasil Diubah!', 'success')
    return redirect(url_for('views.profil', id=id))

@views.route('/profil/<string:id>/update_profil', methods=['POST'])
def update_profile(id):
    user = Masyarakat.query.get_or_404(id)
    if request.method == 'POST':
        nama_lengkap = request.form.get('nama_lengkap')
        username = request.form.get('username')
        alamat = request.form.get('alamat')
        no_telepon = request.form.get('no_telepon')

        # Validasi (Anda dapat menambahkan validasi lain di sini jika diperlukan)

        user.nama_lengkap = nama_lengkap
        user.username = username
        user.alamat = alamat
        user.no_telepon = no_telepon
        db.session.commit()
        flash('Informasi pribadi Anda berhasil diubah!', 'success')
        return redirect(url_for('views.profil', id=id))
        # return jsonify({'success': True, 'message': 'Informasi pribadi Anda berhasil diubah!'})

@views.route('/profil/<string:id>/update_email', methods=['POST'])
def update_email(id):
  user = Masyarakat.query.get_or_404(id)
  if request.method == 'POST':
      email = request.form.get('email')
      password = request.form.get('password')
      
      if email == user.email:
        return jsonify({'success': False, 'email_error': 'Email Anda masih sama, silakan perbarui ke email yang baru.'})
      
      existing_user = Masyarakat.query.filter_by(email=email).first()
      if existing_user:
        return jsonify({'success': False, 'email_error': 'Email sudah ada, silakan ubah email Anda!'})

      if not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'password_error': 'Konfirmasi kata sandi tidak sesuai!'})

      user.email = email
      db.session.commit()
      return jsonify({'success': True, 'message': 'Informasi akun anda berhasil diubah!'})

  return redirect(url_for('views.profil', id=user.user_id))


# todo ====================== END OF PROFILE SECTION ======================
#      ====================================================================
# todo ========================== ADMIN SECTION ===========================

@views.route('/add_tps', methods=['GET','POST'])
def add_tps_location():

    tps = TPS.query.all()

    nama = request.form.get('nama_tps')
    alamat = request.form.get('alamat')
    lat = request.form.get('latitude')
    long = request.form.get('longitude')
    jenis = request.form.get('jenis_sampah')
    open_time = request.form.get('jam_operasional_start')
    close_time = request.form.get('jam_operasional_end')

    if request.method == 'POST':
        add_tps = TPS(nama=nama, alamat=alamat, latitude=lat, longitude=long, jenis_sampah=jenis, jam_operasional_start=open_time, jam_operasional_end=close_time)
        db.session.add(add_tps)
        db.session.commit()
        flash('Berhasil Tambah Data TPS')
        print('Berhasil Tambah Data TPS')
        redirect(url_for('views.add_tps_location'))

    return render_template('add_tps_location.html', page='add_tps', tps=tps)

@views.route('/delete_tps/<string:id>', methods=['POST','GET'])
def delete_tps(id):
    tps = TPS.query.get_or_404(id)
    db.session.delete(tps)
    db.session.commit()
    flash(f'Data TPS {tps.nama} dihapus!', 'danger')
    print('Berhasil Hapus Data TPS')
    redirect(url_for('views.add_tps_location'))

@views.route('/posts', methods=['GET', 'POST'])
def posts():
    if request.method == 'POST':
        judul = request.form.get('judul')
        konten = request.form.get('ckeditor')
        thumbnail = request.files.get('thumbnail')

        if thumbnail and picture_allowed_file(thumbnail.filename):
            filename = secure_filename(thumbnail.filename)
            thumbnail_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            thumbnail.save(thumbnail_path)
            thumbnail_db_path = '/static/uploads/' + filename # Simpan path ke database
        else:
            thumbnail_db_path = None  # Tidak ada thumbnail

        add_post = Artikel(judul=judul, konten=konten, thumbnail=thumbnail_db_path)
        db.session.add(add_post)
        db.session.commit()

        flash('Berhasil membuat artikel!', 'success')
        return redirect(url_for('views.posts'))

    post = Artikel.query.all()
    return render_template('post.html', post=post)

@views.route('/posts/read_posts/<string:id>', methods=['GET'])
def read_post(id):
    posts = Artikel.query.get_or_404(id)
    return render_template('post.html', posts=posts)

@views.route('/posts/update/<string:id>', methods=['POST', 'GET'])
def update_post():
    return render_template('post.html')

@views.route('/posts/delete/<string:id>', methods=['POST', 'GET'])
def delete_post(id):
    post = Artikel.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash(f'Postingan dengan judul {post.judul} dihapus!', 'danger')
    return redirect(url_for('views.posts'))

# ==================== USER LEGAL INFORMATIONS ====================
@views.route('/terms_of_use')
def terms_of_use():
    return render_template('terms_of_use.html')

@views.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')