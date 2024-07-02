import uuid

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from App import db, login_manager

# Tabel Identifier untuk User
class User(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_type = db.Column(db.String(20), nullable=False)  # 'masyarakat' atau 'petugas'
    
    # Relationships
    masyarakat = db.relationship('Masyarakat', backref='user', uselist=False)
    petugas = db.relationship('Petugas', backref='user', uselist=False)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class TPS(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=True)  # Opsional: Jika ingin menyimpan alamat lengkap
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    jenis_sampah = db.Column(db.String(255), nullable=True)  # Contoh: 'Organik, Anorganik'
    jam_operasional_start = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'
    jam_operasional_end = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'

class AppAdmin(db.Model, UserMixin):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# Tabel untuk data Masyarakat
class Masyarakat(db.Model, UserMixin):
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_lengkap = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    # ...atribut lain

    def get_id(self):
        return str(self.user_id)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Petugas(db.Model, UserMixin):
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_petugas = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    area_tugas = db.Column(db.String(100), nullable=False)
    # ...atribut lain

    def get_id(self):
        return str(self.user_id)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Laporan(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    masyarakat_id = db.Column(db.String(36), db.ForeignKey('masyarakat.user_id'), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    tanggal_laporan = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(50), nullable=False, default='1')
    foto = db.Column(db.String(255), nullable=True)
    berat = db.Column(db.Float, nullable=True)  # Dalam kilogram
    jenis_sampah = db.Column(db.String(50), nullable=True)

    masyarakat = db.relationship('Masyarakat', backref='laporan')

class Artikel(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thumbnail = db.Column(db.String(255), nullable=True)
    judul = db.Column(db.String(255), nullable=False)
    konten = db.Column(db.Text(), nullable=False)

# === Model Baru untuk Faktor Emisi CO2 ===
class FaktorEmisiCO2(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jenis_sampah = db.Column(db.String(50), unique=True, nullable=False)
    faktor_co2 = db.Column(db.Float, nullable=False)  # CO2 yang dihemat per kg

# === Model Baru untuk Sampah yang Disetor ===
# class SampahDisetor(db.Model):
#     id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     masyarakat_id = db.Column(db.String(36), db.ForeignKey('masyarakat.user_id'), nullable=False)
#     foto = db.Column(db.String(255), nullable=False)
#     berat = db.Column(db.Float, nullable=False)  # Dalam kilogram
#     latitude = db.Column(db.Float, nullable=True)  # Tambahkan atribut latitude
#     longitude = db.Column(db.Float, nullable=True)  # Tambahkan atribut longitude
#     jenis_sampah = db.Column(db.String(50), nullable=False)
#     tanggal_setor = db.Column(db.DateTime, default=datetime.now)

#     masyarakat = db.relationship('Masyarakat', backref='sampah_disetor')

@login_manager.user_loader
def load_user(user_id):
    # Cari user berdasarkan user_id
    user = User.query.get(user_id)

    # Jika user ditemukan, kembalikan objek Masyarakat atau Petugas
    if user:
        if user.user_type == 'masyarakat':
            return user.masyarakat
        elif user.user_type == 'petugas':
            return user.petugas

    # Jika user tidak ditemukan, kembalikan None
    return None
