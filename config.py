import os
from datetime import timedelta

GCS_BUCKET_NAME = "sns_application_ver2"
GCS_PROJECT_ID   = "ver2-459602"

class Config:
    # データベース設定
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Aki120124@localhost:5432/sns_application'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # セキュリティ設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7) 