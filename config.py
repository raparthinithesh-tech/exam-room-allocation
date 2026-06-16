import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam_portal_secret_2024')

    # PostgreSQL connection URL (set this in Render environment variables)
    # Format: postgresql://user:password@host:port/dbname
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # Fallback SQLite for local development (when DATABASE_URL is not set)
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'exam_portal.db')

    # Admin credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
