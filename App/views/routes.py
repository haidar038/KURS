from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for, current_app
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
# Import other necessary modules and models
from App.models import TPS, Artikel, Laporan
from App import db

import secrets, os, json

views = Blueprint('views', __name__)

PICTURE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

def picture_allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PICTURE_ALLOWED_EXTENSIONS

@views.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@views.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')

@views.route('/')
def index():
    tps = TPS.query.all()
    artikel = Artikel.query.all()

    nama_tps = [namaTPS.nama for namaTPS in tps]
    lat_tps = [latTPS.latitude for latTPS in tps]
    long_tps = [longTPS.longitude for longTPS in tps]

    return render_template('index.html', nama_tps=json.dumps(nama_tps), lat_tps=json.dumps(lat_tps), long_tps=json.dumps(long_tps), tps=tps, artikel=artikel, page='home')

@views.route('/wiki', methods=['GET','POST'])
def wiki():
    artikel = Artikel.query.all()
    return render_template('wiki.html', artikel=artikel, page='wiki') 

@views.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
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

@views.route('/riwayat', methods=['GET', 'POST'])
@login_required
def history():
    data_laporan = Laporan.query.filter_by(masyarakat_id=current_user.user_id).all()

    status = [laporan.status for laporan in data_laporan]
    lat_tps = [laporan.latitude for laporan in data_laporan]
    long_tps = [laporan.longitude for laporan in data_laporan]

    return render_template('history.html', 
                           data_laporan=data_laporan, 
                           status=json.dumps(status), 
                           lat_tps=json.dumps(lat_tps), 
                           long_tps=json.dumps(long_tps), 
                           page='history')

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