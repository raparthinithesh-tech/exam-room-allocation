import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam_portal_secret_2024')

    # On Render, store DB on the persistent disk at /data
    # Locally, store in the project folder
    _db_dir = '/data' if os.path.isdir('/data') else os.path.dirname(__file__)
    DATABASE = os.path.join(_db_dir, 'exam_portal.db')

    # Admin credentials — set via Render environment variables
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
