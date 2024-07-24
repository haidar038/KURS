import uuid

from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from datetime import datetime
from . import db  # Ensure correct relative import

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_type = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    # masyarakat = db.relationship('Masyarakat', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan")
    # petugas = db.relationship('Petugas', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan")
    # app_admin = db.relationship('AppAdmin', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan") 

    # @hybrid_property
    # def password(self):
    #     raise AttributeError('password is not a readable attribute')

    # @password.setter
    # def password(self, password):
    #     self.password_hash = generate_password_hash(password)

    # def verify_password(self, password):
    #     return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        """Generate a reset password token that expires after the specified time."""
        return URLSafeTimedSerializer(current_app.config['SECRET_KEY']).dumps(
            {'user_id': self.id},
            salt=current_app.config['SECURITY_PASSWORD_SALT']
        )

    @staticmethod
    def verify_reset_password_token(token):
        """Verify a password reset token and return the associated user."""
        try:
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            data = serializer.loads(
                token,
                salt=current_app.config['SECURITY_PASSWORD_SALT'],
                max_age=600  # Token valid for 10 minutes
            )
            user_id = data.get('user_id')
            if user_id is None:
                return None
            user = User.query.get(user_id)
            return user
        except SignatureExpired:
            return None  # Token expired
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None

class AppAdmin(db.Model, UserMixin):
    __tablename__ = 'app_admin'
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, default=lambda: str(uuid.uuid4()))
    foto_profil = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('admin', uselist=False))

    def get_id(self):
        return str(self.user_id)

# Tabel untuk data Masyarakat
class Masyarakat(db.Model, UserMixin):
    __tablename__ = 'masyarakat'
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_lengkap = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    foto_profil = db.Column(db.String(255), nullable=True)
    poin = db.Column(db.Integer, default=0) # Atribut baru untuk poin

    user = db.relationship('User', backref=db.backref('masyarakat', uselist=False))

    def get_id(self):
        return str(self.user_id)
    
    def tambah_poin(self, jumlah_poin=15):
        """Menambahkan poin ke user Masyarakat."""
        self.poin += jumlah_poin
        db.session.commit()

class Petugas(db.Model, UserMixin):
    __tablename__ = 'petugas'
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_petugas = db.Column(db.String(100), nullable=False)
    area_tugas = db.Column(db.String(100), nullable=False)
    no_telepon = db.Column(db.String(20), nullable=False)
    foto_profil = db.Column(db.String(255), nullable=True)
    poin = db.Column(db.Integer, default=0)  # Tambahkan atribut poin

    user = db.relationship('User', backref=db.backref('petugas', uselist=False))

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
    is_paid = db.Column(db.Boolean, nullable=False, default=False)

    masyarakat = db.relationship('Masyarakat', backref='laporan')
    petugas = db.relationship('Petugas', backref='laporan')  # Relasi ke model Petugas
    tps = db.relationship('TPS', backref='laporan')  # Relasi ke model Petugas

class TPS(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama = db.Column(db.String(100), nullable=False)
    alamat = db.Column(db.Text, nullable=True)  # Opsional: Jika ingin menyimpan alamat lengkap
    foto = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    jenis_sampah = db.Column(db.String(255), nullable=True)  # Contoh: 'Organik, Anorganik'
    # jam_operasional_start = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'
    # jam_operasional_end = db.Column(db.String(100), nullable=True)  # Contoh: '08:00 - 17:00'

class Artikel(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thumbnail = db.Column(db.String(255), nullable=True)
    judul = db.Column(db.String(255), nullable=False)
    konten = db.Column(db.Text(), nullable=False)

class Notification(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)  # Who is the notification for?
    sender_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)     # Who sent it?
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    is_read = db.Column(db.Boolean, default=False)  # Mark as read or unread

    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='notifications_received')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='notifications_sent')

# === Model Baru untuk Faktor Emisi CO2 ===
class FaktorEmisiCO2(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    jenis_sampah = db.Column(db.String(50), unique=True, nullable=False)
    faktor_co2 = db.Column(db.Float(20), nullable=False)  # CO2 yang dihemat per kg

# === Model Untuk Misi, Poin & Reward

class Misi(db.Model):
    __tablename__ = 'misi'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_misi = db.Column(db.String(100), nullable=False)
    deskripsi = db.Column(db.Text, nullable=False)
    poin = db.Column(db.Integer, nullable=False)
    frekuensi = db.Column(db.String(50), nullable=False)  # Contoh: 'Harian', '2 kali seminggu'

class ProgressMisi(db.Model):
    __tablename__ = 'progress_misi'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    masyarakat_id = db.Column(db.String(36), db.ForeignKey('masyarakat.user_id'), nullable=False)
    misi_id = db.Column(db.String(36), db.ForeignKey('misi.id'), nullable=False)
    tanggal_selesai = db.Column(db.Date, nullable=True) # Tanggal misi diselesaikan
    status = db.Column(db.String(20), nullable=False, default='Belum Selesai') # Status: 'Selesai', 'Belum Selesai'

    misi = db.relationship('Misi', backref='progress_misi', lazy=True) 

class Reward(db.Model):
    __tablename__ = 'reward'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nama_reward = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.Text, nullable=True)
    poin_diperlukan = db.Column(db.Integer, nullable=False)
    # Anda dapat menambahkan kolom lain sesuai kebutuhan, seperti gambar reward.

class RiwayatReward(db.Model):
    __tablename__ = 'riwayat_reward'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    reward_id = db.Column(db.String(36), db.ForeignKey('reward.id'), nullable=False)
    tanggal_klaim = db.Column(db.DateTime, default=datetime.now)