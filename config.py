import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam_portal_secret_2024')
    DATABASE = os.path.join(os.path.dirname(__file__), 'exam_portal.db')

    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
