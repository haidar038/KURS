import io, os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash
from flask_toastr import Toastr
from flask_migrate import Migrate
from flask_ckeditor import CKEditor
from dotenv import load_dotenv

app = Flask(__name__)

socketio = SocketIO(cors_allowed_origins="*")
db = SQLAlchemy()
ckeditor = CKEditor()
login_manager = LoginManager()
toastr = Toastr()
buffer = io.BytesIO()
migrate = Migrate(app, db)
load_dotenv()

def create_app():
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "kursampah") # Gunakan variabel environment atau nilai default
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{os.environ.get("MYSQLUSER")}:{os.environ.get("MYSQLPASSWORD")}@{os.environ.get("MYSQLHOST")}:{os.environ.get("MYSQLPORT")}/{os.environ.get("MYSQLDATABASE")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CKEDITOR_PKG_TYPE'] = 'basic'

    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    ckeditor.init_app(app)
    toastr.init_app(app)

    # from .auth.routes import auth
    # from .admin.routes import admin_page
    from .views.routes import views

    # app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    # app.register_blueprint(admin_page, url_prefix='/')

    login_manager.login_view = 'auth.login'

    from .models import AppAdmin

    with app.app_context():
        db.create_all()

        if not AppAdmin.query.first():
            admin_query = AppAdmin(username='admin', password_hash=generate_password_hash('admkurs123', method='pbkdf2'))
            db.session.add(admin_query)
            db.session.commit()

    return app