import os

from collections import defaultdict
from flask import request, redirect, render_template, Blueprint, flash, url_for, current_app, send_from_directory, jsonify, g
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from flask_socketio import emit
from flask_login import login_required, current_user

from App.models import TPS, Artikel, Laporan, Petugas, Masyarakat, User, AppAdmin, FaktorEmisiCO2, Notification
from App.utils import get_user_notification_room, get_unread_notifications
from App import db

app_admin = Blueprint('app_admin', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS
def picture_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

pagination_pages = 8

def hitung_emisi_ch4(berat_sampah, doc=0.5, r=0.3, o=0.0):
    """Menghitung emisi CH4 dari sampah organik menggunakan metode IPPC.

    Args:
        berat_sampah (float): Berat sampah organik dalam ton.
        doc (float): Fraksi bahan organik terlarut (default: 0.5).
        r (float): Fraksi sampah yang direduksi melalui dekomposisi (default: 0.3).
        o (float): Fraksi sampah yang teroksidasi melalui pembakaran (default: 0.0).

    Returns:
        float: Emisi CH4 dalam ton.
    """
    emisi_ch4 = 1.0 * berat_sampah * doc * (1 - r) * (1 - o)
    return emisi_ch4

def hitung_co2_dihemat(jenis_sampah, berat_sampah):
    """Menghitung CO2 yang dihemat."""

    try:
        # Ambil faktor emisi dari database
        faktor_emisi = FaktorEmisiCO2.query.filter_by(jenis_sampah=jenis_sampah).one().faktor_co2
        
        # Lakukan perhitungan jika faktor emisi ditemukan
        co2_dihemat = faktor_emisi * berat_sampah * 25 # Konversi CH4 ke CO2
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

    
@app_admin.context_processor
def inject_unread_notifications():
  if current_user.is_authenticated:
    unread_notifications = get_unread_notifications()
  else:
    unread_notifications = []
  return dict(unread_notifications=unread_notifications)

@app_admin.route('/admin/data/<string:data_type>')
@login_required
def get_admin_data(data_type):
    page = request.args.get('page', 1, type=int)

    if data_type == 'user':
        pagination = Masyarakat.query.paginate(page=page, per_page=pagination_pages)
        data = [{'index': i, 'nama': item.nama_lengkap, 'alamat': item.alamat, 'poin': item.poin} for i, item in enumerate(pagination.items, start=1)]
    elif data_type == 'officer':
        pagination = Petugas.query.paginate(page=page, per_page=pagination_pages)
        data = [{'index': i, 'nama': item.nama_petugas, 'area': item.area_tugas, 'poin': item.poin} for i, item in enumerate(pagination.items, start=1)]
    elif data_type == 'tps':
        pagination = TPS.query.paginate(page=page, per_page=pagination_pages)
        data = []
        for i, item in enumerate(pagination.items, start=1):
            # Hitung total_sampah menggunakan query SQLAlchemy
            total_sampah = db.session.query(db.func.sum(Laporan.berat)).filter(Laporan.tps_id == item.id).scalar() or 0
            data.append({
                'index': i, 
                'tps': item.nama, 
                'alamat': item.alamat, 
                'total_sampah': total_sampah
            })
    else:
        return jsonify({'error': 'Invalid data type'}), 400

    return jsonify({
        'data': data,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'page': pagination.page,
        'pages': pagination.pages
    })


@app_admin.route('/admin_page')
@login_required
def index():
    user = Masyarakat.query.all()
    officer = Petugas.query.all()
    sampah = Laporan.query.filter_by(status='3').all()
    tps = TPS.query.all()
    artikel = Artikel.query.all()
    user_type = User.query.filter_by(id=current_user.id).first()

    if user_type.user_type == 'masyarakat':
        return redirect(url_for('views.index'))
    elif user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))

    # Emit joined_room event for AppAdmin
    room = get_user_notification_room(current_user.id)
    emit('joined_room', {'room': room}, room=room, namespace='/')

    data_sampah = defaultdict(float)
    for laporan in sampah:
        data_sampah[laporan.jenis_sampah] += laporan.berat

    total_ch4_dihemat = 0
    for laporan in sampah:
        if laporan.jenis_sampah == 'Organik':  # Hanya hitung untuk sampah organik
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton
        elif laporan.jenis_sampah == 'Anorganik':  # Hanya hitung untuk sampah anorganik
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton
        elif laporan.jenis_sampah == 'Campuran':  # Hanya hitung untuk sampah campuran
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton

    total_co2_dihemat = 0
    for jenis_sampah, berat_sampah in data_sampah.items():
        total_co2_dihemat += hitung_co2_dihemat(jenis_sampah, berat_sampah)

    total_vol_sampah = sum([sumSampah.berat for sumSampah in sampah])

    return render_template(
        'admin_page/index.html',
        round=round,
        user=user,
        user_data=jsonify(get_admin_data('user').json).json,
        officer_data=jsonify(get_admin_data('officer').json).json,
        tps_data=jsonify(get_admin_data('tps').json).json,
        total_vol_sampah=total_vol_sampah,
        total_ch4_dihemat=total_ch4_dihemat,
        total_co2_dihemat=total_co2_dihemat,
        unread_notifications=get_unread_notifications(),
        officer=officer,
        sampah=sampah,
        tps=tps, 
        artikel=artikel,
        page='home')

@app_admin.route('/admin_page/stats', methods=['GET', 'POST'])
@login_required
def stats():
    # FOR REPORT CHART

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

    return render_template(
        'admin_page/stats.html',
        page='stats',
        laporan_per_hari=laporan_per_hari
        )

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
    foto = request.files.get('foto')
    lat = request.form.get('latitude')
    long = request.form.get('longitude')
    jenis = request.form.get('jenis_sampah')
    # open_time = request.form.get('jam_operasional_start')
    # close_time = request.form.get('jam_operasional_end')

    if request.method == 'POST':
        if foto and picture_allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            foto_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            foto.save(foto_path)
            foto_db_path = '/static/uploads/' + filename # Simpan path ke database
        else:
            foto_db_path = None  # Tidak ada foto

        add_tps = TPS(nama=nama, alamat=alamat, latitude=lat, longitude=long, jenis_sampah=jenis, foto=foto_db_path)
        db.session.add(add_tps)
        db.session.commit()
        flash('Berhasil Menambahkan Data TPS', 'success')
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

@app_admin.route('/admin_page/update_tps/<string:id>', methods=['POST','GET'])
def update_tps(id):
    tps = TPS.query.get_or_404(id)
    
    nama = request.form['nama_tps_update']
    alamat = request.form['alamat_update']
    foto = request.files.get('foto_update')
    latitude = request.form['latitude_update']
    longitude = request.form['longitude_update']
    jenis_sampah = request.form['jenis_sampah_update']

    if request.method == 'POST':
        tps.nama = nama
        tps.alamat = alamat
        tps.latitude = latitude
        tps.longitude = longitude
        tps.jenis_sampah = jenis_sampah

        if foto and picture_allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            foto_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            foto.save(foto_path)
            foto_db_path = '/static/uploads/' + filename # Simpan path ke database
            tps.foto = foto_db_path
        else:
            foto_db_path = None  # Tidak ada foto
        
        db.session.commit()

        flash(f'Data TPS {tps.nama} berhasil diperbarui!', 'success')
        print('Berhasil Perbarui Data TPS')
        return redirect(url_for('app_admin.tps'))

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

        # Send notification to all users 
        # You might want to refine this to target specific user segments
        for user in User.query.all():  
            notification = Notification(
                recipient_id=user.id,
                sender_id=current_user.id,
                message="Artikel baru telah diposting!" 
            )
            db.session.add(notification)
        db.session.commit() 

        # Emit SocketIO event to all users (or adjust the room as needed)
        emit('new_article', {'message': 'Artikel baru tersedia!'}, room='all_users', namespace='/') 

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


# todo ====================== NOTIFICATION SECTION ===========================

@app_admin.route('/notification/<string:notification_id>/mark_as_read', methods=['POST', 'GET'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    notification.is_read = True
    db.session.commit()

    return redirect(url_for('app_admin.index'))


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