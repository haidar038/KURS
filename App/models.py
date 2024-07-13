import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from . import db  # Ensure correct relative import

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_type = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    masyarakat = db.relationship('Masyarakat', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan")
    petugas = db.relationship('Petugas', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan")
    app_admin = db.relationship('AppAdmin', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan") 

    # @hybrid_property
    # def password(self):
    #     raise AttributeError('password is not a readable attribute')

    # @password.setter
    # def password(self, password):
    #     self.password_hash = generate_password_hash(password)

    # def verify_password(self, password):
    #     return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def get_id(self):
        return str(self.id)

class AppAdmin(db.Model, UserMixin):
    __tablename__ = 'app_admin'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)

    foto_profil = db.Column(db.String(255), nullable=True)

    # user = db.relationship('User', backref=db.backref('admin', uselist=False))

    def __repr__(self):
        return f'<AppAdmin {self.id}>' 

    def get_id(self):
        return str(self.user_id)

# Tabel untuk data Masyarakat
class Masyarakat(db.Model, UserMixin):
    __tablename__ = 'masyarakat'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)

    nama_lengkap = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    foto_profil = db.Column(db.String(255), nullable=True)
    poin = db.Column(db.Integer, default=0) # Atribut baru untuk poin

    # user = db.relationship('User', backref=db.backref('masyarakat', uselist=False))

    def __repr__(self):
        return f'<Masyarakat {self.nama_lengkap}>'

    def get_id(self):
        return str(self.user_id)
    
    def tambah_poin(self, jumlah_poin=15):
        """Menambahkan poin ke user Masyarakat."""
        self.poin += jumlah_poin
        db.session.commit()

class Petugas(db.Model, UserMixin):
    __tablename__ = 'petugas'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'), unique=True, nullable=False)

    nama_petugas = db.Column(db.String(100), nullable=False)
    area_tugas = db.Column(db.String(100), nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    foto_profil = db.Column(db.String(255), nullable=True)
    poin = db.Column(db.Integer, default=0)  # Tambahkan atribut poin

    # user = db.relationship('User', backref=db.backref('petugas', uselist=False))

    def __repr__(self):
        return f'<Petugas {self.nama_petugas}>'

    def get_id(self):
        return str(self.user_id)
    
    def tambah_poin(self, jumlah_poin=10):  # Method untuk menambah poin 
        """Menambahkan poin ke Petugas."""
        self.poin += jumlah_poin
        db.session.commit()

class Laporan(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    masyarakat_id = db.Column(db.String(36), db.ForeignKey('masyarakat.user_id'), nullable=False)
    petugas_id = db.Column(db.String(36), db.ForeignKey('petugas.user_id'), nullable=True)
    tps_id = db.Column(db.String(36), db.ForeignKey('tps.id'), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    tanggal_laporan = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(50), nullable=False, default='1')
    foto = db.Column(db.String(255), nullable=True)
    berat = db.Column(db.Float, nullable=True)  # Dalam kilogram
    jenis_sampah = db.Column(db.String(50), nullable=True)

    masyarakat = db.relationship('Masyarakat', backref='laporan')
    petugas = db.relationship('Petugas', backref='laporan')  # Relasi ke model Petugas
    tps = db.relationship('TPS', backref='laporan')  # Relasi ke model Petugas

class TPS(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=True)  # Opsional: Jika ingin menyimpan alamat lengkap
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    jenis_sampah = db.Column(db.String(255), nullable=True)  # Contoh: 'Organik, Anorganik'
    jam_operasional_start = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'
    jam_operasional_end = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'

class Artikel(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thumbnail = db.Column(db.String(255), nullable=True)
    judul = db.Column(db.String(255), nullable=False)
    konten = db.Column(db.Text(), nullable=False)

# === Model Baru untuk Faktor Emisi CO2 ===
class FaktorEmisiCO2(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jenis_sampah = db.Column(db.String(50), unique=True, nullable=False)
    faktor_co2 = db.Column(db.Float(20), nullable=False)  # CO2 yang dihemat per kg

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