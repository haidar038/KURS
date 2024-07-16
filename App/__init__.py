import io, os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash
from flask_toastr import Toastr
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import create_engine

load_dotenv()

# Use a default port if MYSQLPORT is not set
mysql_port = os.environ.get("MYSQLPORT", "3306")

mysql_uri = (f'mysql+pymysql://{os.environ.get("MYSQLUSER")}:'
        f'{os.environ.get("MYSQLPASSWORD")}@'
        f'{os.environ.get("MYSQLHOST")}:'
        f'{mysql_port}/'
        f'{os.environ.get("MYSQLDATABASE")}')

socketio = SocketIO(cors_allowed_origins="*")
db = SQLAlchemy()
ckeditor = CKEditor()
login_manager = LoginManager()
toastr = Toastr()
mail = Mail()
migrate = Migrate()

# Create engine only if all necessary environment variables are set
if all([os.environ.get("MYSQLUSER"), os.environ.get("MYSQLPASSWORD"),
        os.environ.get("MYSQLHOST"), os.environ.get("MYSQLDATABASE")]):
    engine = create_engine(mysql_uri)
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=f"mysql://{mysql_uri}",
        storage_options={"engine": engine}
    )
else:
    print("Warning: MySQL environment variables are not fully set. Limiter will use in-memory storage.")
    limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)

    UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Pastikan folder ada

    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "kursampah")  # Gunakan variabel environment atau nilai default
    app.config['SQLALCHEMY_DATABASE_URI'] = mysql_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CKEDITOR_PKG_TYPE'] = 'basic'
    app.config['CKEDITOR_ENABLE_CSRF'] = True
    app.config['CKEDITOR_SERVE_LOCAL'] = True
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Konfigurasi folder upload

    # EMAIL CONFIRMATION
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_DEFAULT_SENDER')

    print(f"Email User: {os.environ.get('EMAIL_USER')}")
    print(f"Email Pass: {os.environ.get('EMAIL_PASS')}")

    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    toastr.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    from .Authentication.routes import auth
    from .Officer.routes import officer
    from .Admin.routes import app_admin
    from .views.routes import views

    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(officer, url_prefix='/')
    app.register_blueprint(app_admin, url_prefix='/')

    login_manager.login_view = 'auth.login'

    from .models import AppAdmin, User, FaktorEmisiCO2

    with app.app_context():
        db.create_all()

        if not User.query.filter_by(user_type='admin').first():
            try:
                new_user = User(
                    user_type='admin',
                    username='admin',
                    email='admin@gmail.com',
                    password_hash=generate_password_hash('admkurs123', method='pbkdf2'),
                    is_confirmed = True,
                    confirmed_on = datetime.now()
                )
                db.session.add(new_user) 
                db.session.flush()  

                admin_data = AppAdmin(
                    user_id=new_user.id
                )
                db.session.add(admin_data)
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                print(f"Error during adding admin data: {e}") 

        # Add Default CO2 Emission Factor if not available
        if not FaktorEmisiCO2.query.all():
            default_faktor = [
                {"jenis_sampah": "Organik", "faktor_co2": 0.5},  # Example value
                {"jenis_sampah": "Anorganik", "faktor_co2": 0.2}  # Example value
                # Add other waste types and their CO2 emission factors as needed
            ]
            
            for faktor in default_faktor:
                new_faktor = FaktorEmisiCO2(
                    jenis_sampah=faktor['jenis_sampah'],
                    faktor_co2=faktor['faktor_co2']
                )
                db.session.add(new_faktor)

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error during adding default CO2 emission factors: {e}") 

    return app
