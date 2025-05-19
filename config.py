import os
from datetime import timedelta

GCS_BUCKET_NAME = "sns_application_ver2"
GCS_PROJECT_ID   = "ver2-459602"

class Config:
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('postgresql://sns_user:2IkOtyBvsxSKjHbaIk0h9TgJVlvN0a5v@dpg-d0lda2ffte5s739df1bg-a/sns_db_yqls')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # セキュリティ設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7) 