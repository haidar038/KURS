from flask import Blueprint, render_template, send_file, request, redirect, flash, url_for
# Import other necessary modules and models
from App.models import TPS, Artikel
from App import db

views = Blueprint('views', __name__)

@views.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@views.route('/sw.js')
def serve_sw():
    return send_file('sw.js', mimetype='application/javascript')

@views.route('/')
def index():
    data_tps = [
        {"id": 1, "nama": "TPS Gambesi", "latitude": "0.7552107801638247", "longitude": "127.33604266194835"},
    ]
    tps = TPS.query.all()
    artikel = Artikel.query.all()

    return render_template('base.html', data_tps=data_tps, tps=tps, artikel=artikel, page='home')

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

@views.route('/delete_tps/<int:id>', methods=['POST','GET'])
def delete_tps(id):
    tps = TPS.query.get_or_404(id)
    db.session.delete(tps)
    db.session.commit()
    flash(f'Data TPS {tps.nama} dihapus!', 'danger')
    print('Berhasil Hapus Data TPS')
    redirect(url_for('views.add_tps_location'))

@views.route('/posts', methods=['GET'])
def posts():
    posts = Artikel.query.all()
    return render_template('posts.html', posts=posts)

@views.route('/posts/read_posts/<int:id>', methods=['GET'])
def read_post(id):
    posts = Artikel.query.get_or_404(id)
    return render_template('posts.html', posts=posts)

@views.route('/posts/write_post', methods=['POST', 'GET'])
def write_post():
    post = Artikel.query.all()

    if request.method == 'POST':
        judul = request.form.get('judul')
        konten = request.form.get('ckeditor')

        add_post = Artikel(judul=judul, konten=konten)
        db.session.add(add_post)
        db.session.commit()
        flash('Berhasil membuat artikel!', 'success')
        print('Berhasil membuat artikel!')
        return redirect(url_for('views.write_post'))
    return render_template('write_post.html', post=post)

@views.route('/posts/update/<int:id>', methods=['POST', 'GET'])
def update_post():
    return render_template('write_post.html')

@views.route('/posts/delete/<int:id>', methods=['POST', 'GET'])
def delete_post(id):
    post = Artikel.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash(f'Postingan dengan judul {post.judul} dihapus!', 'danger')
    return redirect(url_for('views.write_post'))