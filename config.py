import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask ayarları
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-123'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-key-123'
    
    # Veritabanı ayarları
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "instance", "jewelry.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT ayarları
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Uygulama ayarları
    DEBUG = False
    TESTING = False
    
    # Güvenlik ayarları
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1) 