import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'omnisync-super-secret-key-2026-secure')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'omnisync.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'doc', 'docx', 'zip', 'csv', 'mp3', 'mp4'}

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'uploads'), exist_ok=True)
