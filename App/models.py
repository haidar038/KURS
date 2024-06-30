from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from App import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'masyarakat' atau 'petugas'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class TPS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=True)  # Opsional: Jika ingin menyimpan alamat lengkap
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    jenis_sampah = db.Column(db.String(255), nullable=True)  # Contoh: 'Organik, Anorganik'
    jam_operasional_start = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'
    jam_operasional_end = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'

    # def __init__(self, id, nama, alamat, latitude, longitude, jenis_sampah, jam_operasional_start, jam_operasional_end):
    #     self.id = id
    #     self.nama = nama
    #     self.alamat = alamat
    #     self.jenis_sampah = jenis_sampah
    #     self.latitude = latitude
    #     self.longitude = longitude
    #     self.jam_operasional_start = jam_operasional_start
    #     self.jam_operasional_end = jam_operasional_end
    
    # def to_dict(self):
    #     return {
    #         'id': self.id,
    #         'nama': self.nama,
    #         'alamat': self.alamat,
    #         'jenis_sampah': self.jenis_sampah,
    #         'latitude': self.latitude,
    #         'longitude': self.longitude,
    #         'jam_operasional_start': self.jam_operasional_start,
    #         'jam_operasional_end': self.jam_operasional_end
    #     }

class AppAdmin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Masyarakat(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    # ...atribut lain

    user = db.relationship('User', backref=db.backref('masyarakat', uselist=False))

class Petugas(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    nama_petugas = db.Column(db.String(100), nullable=False)
    area_tugas = db.Column(db.String(100), nullable=False)
    # ...atribut lain

    user = db.relationship('User', backref=db.backref('petugas', uselist=False))

class Laporan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    masyarakat_id = db.Column(db.Integer, db.ForeignKey('masyarakat.user_id'), nullable=False)
    # ...atribut lain sesuai kebutuhan

    masyarakat = db.relationship('Masyarakat', backref='laporan')

class Artikel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thumbnail = db.Column(db.String(255), nullable=True)
    judul = db.Column(db.String(255), nullable=False)
    konten = db.Column(db.Text(), nullable=False)

# === Model Baru untuk Faktor Emisi CO2 ===
class FaktorEmisiCO2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jenis_sampah = db.Column(db.String(50), unique=True, nullable=False)
    faktor_co2 = db.Column(db.Float, nullable=False)  # CO2 yang dihemat per kg

# === Model Baru untuk Sampah yang Disetor ===
class SampahDisetor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    masyarakat_id = db.Column(db.Integer, db.ForeignKey('masyarakat.user_id'), nullable=False)
    foto = db.Column(db.String(255), nullable=False)
    berat = db.Column(db.Float, nullable=False)  # Dalam kilogram
    latitude = db.Column(db.Float, nullable=True)  # Tambahkan atribut latitude
    longitude = db.Column(db.Float, nullable=True)  # Tambahkan atribut longitude
    jenis_sampah = db.Column(db.String(50), nullable=False)
    tanggal_setor = db.Column(db.DateTime, default=datetime.now)

    masyarakat = db.relationship('Masyarakat', backref='sampah_disetor')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ...Rute dan Views (Contoh)