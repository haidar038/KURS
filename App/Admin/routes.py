import os

from collections import defaultdict
from flask import request, redirect, render_template, Blueprint, flash, url_for, current_app, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from flask_login import login_required, current_user

from App.models import TPS, Artikel, Laporan, Petugas, Masyarakat, User, AppAdmin, FaktorEmisiCO2
from App import db

app_admin = Blueprint('app_admin', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS
def picture_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

pagination_pages = 8

def hitung_co2_dihemat(jenis_sampah, berat_sampah):
    """Menghitung CO2 yang dihemat."""

    try:
        # Ambil faktor emisi dari database
        faktor_emisi = FaktorEmisiCO2.query.filter_by(jenis_sampah=jenis_sampah).one().faktor_co2
        
        # Lakukan perhitungan jika faktor emisi ditemukan
        co2_dihemat = faktor_emisi * berat_sampah * 1000
        return co2_dihemat

    except NoResultFound:
        # Tangani jika jenis sampah tidak ada dalam database
        print(f"Faktor emisi untuk jenis sampah '{jenis_sampah}' tidak ditemukan.")
        flash(f"Faktor emisi untuk jenis sampah '{jenis_sampah}' tidak ditemukan.", category='danger')
        return 0.0

    except Exception as e:
        # Tangani error database generik
        print(f"Error database: {e}")
        flash(f"Terjadi kesalahan saat menghitung emisi CO2. Silahkan coba lagi.", category='danger')
        return 0.0

@app_admin.route('/admin_page')
@login_required
def index():
    user = Masyarakat.query.all()
    officer = Petugas.query.all()
    sampah = Laporan.query.filter_by(status='3').all()
    tps = TPS.query.all()
    artikel = Artikel.query.all()

    data_sampah = defaultdict(float)
    for laporan in sampah:
        data_sampah[laporan.jenis_sampah] += laporan.berat 

    total_co2_dihemat = 0
    for jenis_sampah, berat_sampah in data_sampah.items():
        total_co2_dihemat += hitung_co2_dihemat(jenis_sampah, berat_sampah)

    total_vol_sampah = sum([sumSampah.berat for sumSampah in sampah])

    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))

    return render_template('admin_page/index.html', round=round, user=user, total_vol_sampah=total_vol_sampah, total_co2_dihemat=total_co2_dihemat, officer=officer, sampah=sampah, tps=tps, artikel=artikel, page='home')

@app_admin.route('/admin_page/tps', methods=['GET','POST'])
@login_required
def tps():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    
    # tps = TPS.query.all()

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
        flash('Berhasil Tambah Data TPS', 'success')
        print('Berhasil Tambah Data TPS')
        redirect(url_for('app_admin.tps'))

    tps_data = (
        db.session.query(
            TPS,
            func.sum(Laporan.berat).label('total_sampah')
        )
        .outerjoin(Laporan, Laporan.tps_id == TPS.id)  
        .group_by(TPS.id) 
        .all()
    )
    
    tps = [{"tps": item[0], "total_sampah": item[1]} for item in tps_data]

    data_tps = TPS.query.all()
    
    page = request.args.get('page', 1, type=int)
    tps_pagination = TPS.query.paginate(page=page, per_page=pagination_pages)

    return render_template('admin_page/tps.html', page='add_tps', min=min, max=max, tps=tps, data_tps=data_tps, tps_pagination=tps_pagination)

@app_admin.route('/admin_page/delete_tps/<string:id>', methods=['POST','GET'])
def delete_tps(id):
    tps = TPS.query.get_or_404(id)
    db.session.delete(tps)
    db.session.commit()
    flash(f'Data TPS {tps.nama} dihapus!', 'danger')
    print('Berhasil Hapus Data TPS')
    redirect(url_for('app_admin.tps'))


# todo ================================ ARTICLES SECTION ==============================


@app_admin.route('/admin_page/posts', methods=['GET', 'POST'])
def posts():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))

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
        return redirect(url_for('app_admin.posts'))

    post = Artikel.query.all()

    page = request.args.get('page', 1, type=int)
    articles_pagination = Artikel.query.paginate(page=page, per_page=pagination_pages)

    return render_template('admin_page/post.html', min=min, max=max, post=post, articles_pagination=articles_pagination, page_name='articles')

@app_admin.route('/admin_page/posts/read_posts/<string:id>', methods=['GET'])
def read_post(id):
    posts = Artikel.query.get_or_404(id)
    return render_template('post.html', posts=posts)

@app_admin.route('/admin_page/posts/update/<string:id>', methods=['POST', 'GET'])
def update_post():
    return render_template('post.html')

@app_admin.route('/admin_page/posts/delete/<string:id>', methods=['POST', 'GET'])
def delete_post(id):
    post = Artikel.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash(f'Postingan dengan judul {post.judul} dihapus!', 'danger')
    return redirect(url_for('app_admin.posts'))


# todo ================================ PROFILE SECTION ==============================
@app_admin.route('/admin_page/profile/<string:id>', methods=['GET', 'POST'])
@login_required
def profile(id):
    user_type = User.query.get_or_404(id)
    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))

    # user = AppAdmin.query.get_or_404(id)
    return render_template('admin_page/profile.html', page='profile', user=AppAdmin.query.get_or_404(id))

@app_admin.route('/admin_page/profile_picture/<string:id>')
def profile_picture(id):
    """Mengirim foto profil ke halaman web atau gambar default jika tidak ada."""
    user = AppAdmin.query.get_or_404(id)
    if user.foto_profil:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], user.foto_profil)
    else:
        return send_from_directory(current_app.config['STATIC_FOLDER'] + '/img/', 'profile/default.png')  
    
@app_admin.route('/admin_page/profile_picture/update/<string:id>', methods=['POST'])
def update_profile_picture(id):
    user = AppAdmin.query.get_or_404(id)
    foto_profil = request.files.get('foto_profil')
    if foto_profil:
        foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], foto_profil.filename))
        user.foto_profil = foto_profil.filename
        db.session.commit()
        flash('Berhasil memperbarui foto profil', 'success')
        return redirect(url_for('app_admin.profile', id=id))

    if not foto_profil or not allowed_file(foto_profil.filename):
        flash('Foto profil tidak valid!', 'danger')
        return redirect(url_for('app_admin.profile', id=id))
    
    print(id)
    
    filename = secure_filename(foto_profil.filename)
    foto_profil.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

    # update_profile_picture = Petugas(foto_profil=f'/static/img/profile/{filename}')
    
    user.foto_profil = f'/static/img/profile/{filename}'

    flash('Foto Profil Berhasil Diubah!', 'success')
    return redirect(url_for('app_admin.profile', id=id))

@app_admin.route('/admin_page/profile/<string:id>/update_profil', methods=['POST'])
def update_profile(id):
    if request.method == 'POST':
        username = request.form.get('username')

        # Validasi (Anda dapat menambahkan validasi lain di sini jika diperlukan)
        current_user.username = username
        db.session.commit()
        flash('Informasi pribadi Anda berhasil diubah!', 'success')
        return redirect(url_for('app_admin.profile', id=id))
        # return jsonify({'success': True, 'message': 'Informasi pribadi Anda berhasil diubah!'})

@app_admin.route('/admin_page/profile/<string:id>/update_email', methods=['POST'])
def update_email(id):
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == current_user.email:
            return jsonify({'success': False, 'email_error': 'Email Anda masih sama, silakan perbarui ke email yang baru.'})

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'email_error': 'Email sudah ada, silakan ubah email Anda!'})

        if not check_password_hash(current_user.password_hash, password):
            return jsonify({'success': False, 'password_error': 'Konfirmasi kata sandi tidak sesuai!'})

        current_user.email = email
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email berhasil diperbarui.'})
    
    return redirect(url_for('app_admin.profile', id=id))
    
@app_admin.route('/admin_page/profile/<string:id>/update_password', methods=['GET', 'POST'])
def update_password(id):
    user = AppAdmin.query.get_or_404(id)

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if len(new_password) < 8:
            flash('Kata sandi minimal 8 karakter!', 'warning')
            return redirect(url_for('app_admin.profile', id=id))
        

        if not check_password_hash(current_user.password_hash, old_password):
            flash('Kata sandi lama tidak sesuai!', 'warning')
            return redirect(url_for('app_admin.profile', id=id))
        
        if new_password != confirm_password:
            flash('Konfirmasi kata sandi tidak sesuai!', 'warning')
            return redirect(url_for('app_admin.profile', id=id))
        
        
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2')
        db.session.commit()
        
        
        db.session.refresh(current_user)
        
        flash('Kata sandi Anda berhasil diubah!', 'success')
        return redirect(url_for('app_admin.profile', id=id))
    
    return redirect(url_for('app_admin.profile', id=id))