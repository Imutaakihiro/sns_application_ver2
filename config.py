import os
from datetime import timedelta

GCS_BUCKET_NAME = "sns_application_ver2"
GCS_PROJECT_ID   = "ver2-459602"

class Config:
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # セキュリティ設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7) 