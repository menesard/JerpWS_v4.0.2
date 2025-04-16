import os
from flask import Flask, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.utils.helpers import convert_utc_to_local
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import sys
from flask_jwt_extended import JWTManager

# Veritabanı nesnesi oluştur
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
jwt = JWTManager()


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)

    # CORS ayarlarını güncelle
    CORS(app, resources={r"/*": {
        "origins": "*",
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials", "X-Requested-With"],
        "expose_headers": ["Content-Range", "X-Content-Range"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "max_age": 86400
    }})
    # Yapılandırma ayarlarını yükle
    app.config.from_object(config_class)
    app.config.from_pyfile('config.py', silent=True)  # Instance klasöründeki gizli config

    # Session ayarları
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 saat
    app.config['SESSION_COOKIE_SECURE'] = True  # Sadece HTTPS üzerinden
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScript erişimini engelle
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Cross-site güvenliği

    # JWT yapılandırmaları
    app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
    app.config["JWT_SECRET_KEY"] = app.config['SECRET_KEY']
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 saat
    app.config["JWT_COOKIE_SECURE"] = True  # Sadece HTTPS
    app.config["JWT_COOKIE_SAMESITE"] = 'Lax'  # Cross-site güvenliği
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # CSRF koruması aktif
    app.config["JWT_COOKIE_DOMAIN"] = None  # Sadece aynı domain

    # Eklentileri uygulama ile ilişkilendir
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)

    # Loglama yapılandırması
    if not app.debug and not app.testing:
        # Log dizini oluştur
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        # Dosya handler'ı
        file_handler = RotatingFileHandler(
            'logs/jerpws.log',
            maxBytes=5242880,  # 5MB
            backupCount=30,  # 30 yedek dosya
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        # Kritik hatalar için ayrı log dosyası
        error_file_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=1048576,  # 1MB
            backupCount=10,
            encoding='utf-8'
        )
        error_file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        error_file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_file_handler)

        # Konsol handler'ı sadece kritik hatalar için
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        console_handler.setLevel(logging.ERROR)
        app.logger.addHandler(console_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('JerpWS production modunda başlatılıyor...')

    # Blueprint'leri kaydet
    from app.routes.views import main_bp
    app.register_blueprint(main_bp)

    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Veritabanı modellerini içe aktar (migrate için gerekli)
    from app.models import database
    from app.models.database import Setting

    # Shell context oluştur
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': database.User,
            'Setting': database.Setting,
            'Region': database.Region,
            'Transaction': database.Transaction,
            'Customer': database.Customer,
            'GlobalSetting': database.GlobalSetting
        }

    # Template context processor ekle
    @app.context_processor
    def inject_settings():
        settings = Setting.query.all()
        return dict(settings=settings)

    @app.template_filter('localtime')
    def localtime_filter(value):
        """UTC zamanını yerel zamana çeviren şablon filtresi"""
        return convert_utc_to_local(value, 'Europe/Istanbul')

    # Veritabanı oluşturulduğunda varsayılan ayarları ekle
    with app.app_context():
        db.create_all()
        Setting.init_default_settings()
        from app.models.database import init_db
        init_db()

    return app