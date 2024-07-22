from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app, send_from_directory, jsonify, g
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import current_user, login_required
from babel.dates import format_datetime
from flask_socketio import emit
from sqlalchemy.exc import NoResultFound
from collections import defaultdict
from math import radians, sin, cos, sqrt, asin
from datetime import datetime, timedelta
# Import other necessary modules and models
from App.models import TPS, Artikel, Laporan, Masyarakat, User, Notification, Petugas, FaktorEmisiCO2, Misi, ProgressMisi, Reward, RiwayatReward
from App.utils import get_unread_notifications, send_notification
from App import db

import pytz, os, json

views = Blueprint('views', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

pagination_pages = 8

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
    
def reset_misi_harian():
    """Fungsi untuk mereset progress misi harian semua pengguna.

    Fungsi ini akan:
    1. Mengambil semua progress misi dengan tanggal_selesai hari ini.
    2. Mengupdate status progress misi tersebut menjadi 'Belum Selesai'.
    3. Menghapus tanggal_selesai untuk misi harian yang belum diselesaikan.
    4. Menyimpan perubahan ke database.
    """
    now = datetime.now() + timedelta(hours=9)  # Waktu Indonesia Barat (WIB)
    today = now.date()

    progress_misi_hari_ini = ProgressMisi.query.filter_by(tanggal_selesai=today).all()

    for progress in progress_misi_hari_ini:
        if progress.misi.frekuensi == 'Harian':
            if progress.status == 'Belum Selesai':
                # Reset tanggal selesai untuk misi harian yang belum selesai
                progress.tanggal_selesai = None 
            progress.status = 'Belum Selesai'  # Reset status

    db.session.commit()

@views.context_processor
def inject_unread_notifications():
  if current_user.is_authenticated:
    unread_notifications = get_unread_notifications()
  else:
    unread_notifications = []
  return dict(unread_notifications=unread_notifications)

@views.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@views.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Source: https://stackoverflow.com/a/4913653/2447715
    """
    R = 6371  # Radius of earth in kilometers. Use 3956 for miles
    
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))

    return R * c

@views.route('/get_tps_data/<latitude>/<longitude>')
@login_required 
def get_tps_data(latitude, longitude):
    user_latitude = float(latitude)
    user_longitude = float(longitude)
    radius_km = float(request.args.get('radius', default=6)) # Get radius from query parameter

    all_tps = TPS.query.all()

    nearby_tps = []
    for tps in all_tps:
        distance = haversine(user_latitude, user_longitude, tps.latitude, tps.longitude)
        if distance <= radius_km: # Filter based on the radius
            nearby_tps.append({
                'nama': tps.nama,
                'alamat': tps.alamat,
                'latitude': tps.latitude, 
                'longitude': tps.longitude,
                'jarak': round(distance, 2), 
                'waktu_tempuh': int(distance / 40 * 60)
            })

    return jsonify(nearby_tps)

@views.route('/')
@login_required
def index():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    tps = TPS.query.all()
    artikel = Artikel.query.limit(3)
    sampah = Laporan.query.filter_by(status='3').all()

    nama_tps = [namaTPS.nama for namaTPS in tps]
    lat_tps = [latTPS.latitude for latTPS in tps]
    long_tps = [longTPS.longitude for longTPS in tps]
    jumlah_sampah = [jumlahSampah.berat for jumlahSampah in sampah]
    total_berat_sampah = sum(jumlah_sampah)

    # Mengambil data laporan sampah pengguna saat ini
    # laporan_sampah = Laporan.query.filter_by(masyarakat_id=current_user.id).all()
    
    data_sampah = defaultdict(float)
    for laporan in sampah:
        data_sampah[laporan.jenis_sampah] += laporan.berat 

    # Mengambil data laporan sampah pengguna saat ini
    laporan_sampah = Laporan.query.filter_by(masyarakat_id=current_user.id).all()

    total_ch4_dihemat = 0
    for laporan in laporan_sampah:
        if laporan.jenis_sampah == 'Organik':  # Hanya hitung untuk sampah organik
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton
        elif laporan.jenis_sampah == 'Anorganik':  # Hanya hitung untuk sampah anorganik
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton
        elif laporan.jenis_sampah == 'Campuran':  # Hanya hitung untuk sampah campuran
            total_ch4_dihemat += hitung_emisi_ch4(laporan.berat)  # Konversi kg ke ton

    total_co2_dihemat = 0
    for jenis_sampah, berat_sampah in data_sampah.items():
        total_co2_dihemat += hitung_co2_dihemat(jenis_sampah, berat_sampah)

    user = Masyarakat.query.filter_by(user_id=current_user.id).first()

    unread_notifications = get_unread_notifications()

    misi = Misi.query.all()
    # Ambil progress misi untuk user yang login
    progress_user = ProgressMisi.query.filter_by(
        masyarakat_id=current_user.id,
        status='Selesai',
        tanggal_selesai=datetime.now().date()
    ).all()

    # Buat dictionary untuk menyimpan status setiap misi
    misi_status = {}
    for m in misi:
        misi_status[m.id] = False  # Default: misi belum selesai

    # Update status misi berdasarkan progress_user
    for prog in progress_user:
        misi_status[prog.misi_id] = True  # Tandai misi sebagai selesai

    return render_template('index.html',
                            total_co2_dihemat=total_co2_dihemat,
                            total_ch4_dihemat=total_ch4_dihemat,
                            nama_tps=json.dumps(nama_tps),
                            lat_tps=json.dumps(lat_tps),
                            long_tps=json.dumps(long_tps),
                            vol_sampah=total_berat_sampah,
                            tps=tps, # You still might need this for modal or other parts of the page
                            user=user,
                            misi=misi,
                            misi_status=misi_status,
                            artikel=artikel,
                            unread_notifications=unread_notifications,
                            round=round,
                            page='home')


@views.route('/wiki', methods=['GET'])
def wiki():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Jumlah artikel per halaman
    artikel_paginate = Artikel.query.paginate(page=page, per_page=per_page)

    return render_template('wiki.html', min=min, max=max, artikel_paginate=artikel_paginate, page='wiki')

@views.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    if request.method == 'POST':
        # Ambil data dari formulir
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        foto = request.files.get('foto')
        berat = request.form.get('berat')
        jenis_sampah = request.form.get('jenis_sampah')

        # daftar_misi = Misi.query.all()
        misi = Misi.query.filter_by(nama_misi='Setor Sampahmu').first()

        # Validasi data
        if not foto or not allowed_file(foto.filename):
            flash('File foto tidak valid!', 'danger')
            return redirect(url_for('views.reports'))

        # Simpan foto
        filename = secure_filename(foto.filename)
        foto.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        # Tambahkan poin setelah laporan sampah disimpan
        masyarakat = Masyarakat.query.get(current_user.id)  # Ambil objek Masyarakat 
        masyarakat.tambah_poin() # Tambahkan 15 poin (default) 

        # Simpan data ke progres misi
        new_progress = ProgressMisi(
            masyarakat_id=current_user.id,
            misi_id=misi.id,
            tanggal_selesai=datetime.now().date(),
            status='Selesai'
        )
        db.session.add(new_progress)
        db.session.commit()

        # Simpan data ke database (Model Laporan)
        laporan = Laporan(
            masyarakat_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            foto=f'/static/uploads/{filename}',
            berat=berat,
            jenis_sampah=jenis_sampah
        )
        db.session.add(laporan)
        db.session.commit()

        # --- Send notification to relevant officers ---
        officers_in_area = Petugas.query.all() # Assuming area_tugas in Petugas corresponds to report location
        for officer in officers_in_area:
            notification = Notification(
                recipient_id=officer.user_id,
                sender_id=masyarakat.user_id,
                message=f"Laporan baru dibuat oleh {masyarakat.nama_lengkap}",
            )
        db.session.add(notification)
        db.session.commit()

        # Emit SocketIO event (more on this later in JavaScript)
        emit('new_report', {'message': 'Laporan baru tersedia!'}, room='officer_notifications', namespace='/')
        # Emit notification event to the recipient's room 

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

@views.route('/report_picture/<string:id>')
def report_picture(id):
    """Mengirim foto profil ke halaman web atau gambar default jika tidak ada."""
    foto_sampah = Laporan.query.get_or_404(id)
    if foto_sampah.foto:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], foto_sampah.foto)
    else:
        return send_from_directory(current_app.config['STATIC_FOLDER'] + '/img/', 'trash_default.png')

@views.route('/riwayat', methods=['GET', 'POST'])
@login_required
def history():
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    data_laporan = Laporan.query.filter_by(masyarakat_id=current_user.id).all()

    # Format tanggal untuk setiap laporan
    for laporan in data_laporan:
        print(laporan.tps_id)
        laporan.tanggal_laporan = format_tanggal_locale(laporan.tanggal_laporan)

    page = request.args.get('page', 1, type=int)
    laporan_pagination = Laporan.query.filter_by(status='3').paginate(page=page, per_page=pagination_pages)

    return render_template('history.html', laporan_pagination=laporan_pagination, min=min, max=max, data_laporan=data_laporan, page='history')

# todo ====================== NOTIFICATION SECTION ===========================
@views.route('/notification/<string:notification_id>/mark_as_read', methods=['POST', 'GET'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    emit('new_notification', {'count': 1},  room=notification.recipient_id, namespace='/')

    notification.is_read = True
    db.session.commit()

    return jsonify({'success': True})


# todo ====================== POINT & REWARD SYSTEM ==========================


@views.route('/misi')
@login_required
def misi():
    reset_misi_harian()

    daftar_misi = Misi.query.all()
    user = Masyarakat.query.get(current_user.id)

    progress_user = {}
    for misi in daftar_misi:
        # Check if the mission has already been completed today
        progress_today = ProgressMisi.query.filter_by(
            masyarakat_id=current_user.id,
            misi_id=misi.id,
            tanggal_selesai=datetime.now().date()
        ).first()

        progress_user[misi.id] = {
            'misi': misi,
            'status': 'Selesai' if progress_today else 'Belum Selesai'
        }
    
    return render_template('misi.html', 
                            daftar_misi=progress_user, 
                            user=user,
                            page='misi')

@views.route('/selesaikan_misi/<misi_id>', methods=['POST'])
@login_required
def selesaikan_misi(misi_id):
    misi = Misi.query.get_or_404(misi_id)
    user = Masyarakat.query.get(current_user.id)

     # Check if the mission has already been completed today
    progress_today = ProgressMisi.query.filter_by(
        masyarakat_id=current_user.id,
        misi_id=misi.id,
        tanggal_selesai=datetime.now().date()
    ).first()

    if progress_today:
        flash('Misi sudah diselesaikan hari ini!', 'warning')
        return redirect(url_for('views.misi'))
    
    # Contoh validasi: Periksa apakah ada file foto di request
    foto = request.files.get('foto')  
    if not foto:
        flash('Silahkan upload bukti untuk menyelesaikan misi!', 'danger')
        return redirect(url_for('views.misi'))

    # ... (Logika validasi lain sesuai kebutuhan misi, misal: verifikasi foto)

    # Jika validasi berhasil:
    if True: 
        # Update ProgressMisi
        new_progress = ProgressMisi(
            masyarakat_id=current_user.id,
            misi_id=misi.id,
            tanggal_selesai=datetime.now().date(),
            status='Selesai'
        )
        db.session.add(new_progress)

        # Tambahkan poin ke user
        user.poin += misi.poin
        db.session.commit()

        # Send notification
        send_notification(current_user.id, f"Selamat, Anda telah menyelesaikan misi {misi.nama_misi} dan mendapatkan {misi.poin} poin!")
        
        flash('Misi berhasil diselesaikan!', 'success')
        emit('misi_selesai', {'message': 'Misi berhasil diselesaikan!'}, room=current_user.id)
        return redirect(url_for('views.misi'))
    else:
        flash('Gagal menyelesaikan misi.', 'danger')
        return redirect(url_for('views.misi'))

@views.route('/reward')
@login_required
def reward():
    daftar_reward = Reward.query.order_by(Reward.kategori, Reward.nama_reward).all()
    user = Masyarakat.query.get(current_user.id)
    return render_template('reward.html', 
                           daftar_reward=daftar_reward, 
                           user=user,
                           page='reward')

@views.route('/klaim_reward/<reward_id>')
@login_required
def klaim_reward(reward_id):
    reward = Reward.query.get_or_404(reward_id)
    user = Masyarakat.query.get(current_user.id)

    if user.poin >= reward.poin_diperlukan:
        # Kurangi poin user
        user.poin -= reward.poin_diperlukan
        
        # Catat riwayat reward
        riwayat = RiwayatReward(user_id=user.user_id, reward_id=reward.id)
        db.session.add(riwayat)
        db.session.commit()

        send_notification(current_user.id, f"Selamat, Anda telah mengklaim reward {reward.nama_reward}!")
        flash('Reward berhasil diklaim!', 'success')
    else:
        flash('Poin Anda tidak cukup.', 'danger')

    return redirect(url_for('views.reward'))


# todo ====================== PROFILE SECTION ======================


@views.route('/profil/<string:id>', methods=['GET', 'POST'])
@login_required
def profil(id):
    user_type = User.query.filter_by(id=current_user.id).first()
    if user_type.user_type == 'petugas':
        return redirect(url_for('officer.index'))
    elif user_type.user_type == 'admin':
        return redirect(url_for('app_admin.index'))

    user = Masyarakat.query.get_or_404(id)
    return render_template('profile.html', user=user, user_type=user_type, page='profile')

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
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == user.email:
            return jsonify({'success': False, 'email_error': 'Email Anda masih sama, silakan perbarui ke email yang baru.'})
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'email_error': 'Email sudah ada, silakan ubah email Anda!'})

        if not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'password_error': 'Konfirmasi kata sandi tidak sesuai!'})

        user.email = email
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email berhasil diperbarui!'})

    return redirect(url_for('views.profil', id=id))

@views.route('/profil/<string:id>/update_password', methods=['GET', 'POST'])
def update_password(id):
    user = Masyarakat.query.get_or_404(id)
    user_pass = User.query.filter_by(id=user.user_id).first()
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if len(new_password) < 8:
            flash('Kata sandi minimal 8 karakter!', 'warning')
            return redirect(url_for('views.profil', id=id))
        if not check_password_hash(user_pass.password_hash, old_password):
            flash('Kata sandi lama tidak sesuai!', 'warning')
            return redirect(url_for('views.profil', id=id))
        if new_password != confirm_password:
            flash('Konfirmasi kata sandi tidak sesuai!', 'warning')
            return redirect(url_for('views.profil', id=id))
        user_pass.password_hash = generate_password_hash(new_password, method='pbkdf2')
        db.session.commit()
        flash('Kata sandi Anda berhasil diubah!', 'success')
        return redirect(url_for('views.profil', id=id))


# todo ====================== END OF PROFILE SECTION ======================
#      ====================================================================
# todo ========================== ADMIN SECTION ===========================

# ==================== USER LEGAL INFORMATIONS ====================
@views.route('/terms_of_use')
def terms_of_use():
    return render_template('terms_of_use.html')

@views.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')