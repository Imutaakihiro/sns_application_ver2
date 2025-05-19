from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Video
from config import Config
from google.cloud import storage
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import whisper
import tempfile
import subprocess

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# データベースの初期化
db.init_app(app)
migrate = Migrate(app, db)

# ログイン管理の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('このユーザー名は既に使用されています')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に登録されています')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('登録が完了しました')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
            
        flash('ユーザー名またはパスワードが正しくありません')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    # 認証情報ファイルのパスを明示的に指定
    credentials_path = os.path.join(os.path.dirname(__file__), 'ver2-459602-d7fd529371f3.json')
    client = storage.Client.from_service_account_json(credentials_path)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    return f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'wmv', 'flv', 'mkv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def transcribe_video(video_path):
    """
    動画ファイルを文字起こしする関数
    """
    temp_audio_path = None
    try:
        # Whisperモデルの読み込み（tinyモデルを使用）
        model = whisper.load_model("tiny")
        
        # 動画から音声を抽出
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
            # ffmpegを使用して音声を抽出
            ffmpeg_path = os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')
            if not os.path.exists(ffmpeg_path):
                raise FileNotFoundError("ffmpeg.exeが見つかりません")
            
            subprocess.run([
                ffmpeg_path,
                '-y',  # 既存ファイルを上書き
                '-i', video_path,
                '-vn',  # ビデオを無効化
                '-acodec', 'libmp3lame',  # MP3コーデックを使用
                '-ar', '16000',  # サンプルレートを16kHzに設定
                '-ac', '1',  # モノラルに設定
                temp_audio_path
            ], check=True, capture_output=True, text=True)
        
        # 音声ファイルの文字起こし
        result = model.transcribe(temp_audio_path)
        return result["text"]
    except subprocess.CalledProcessError as e:
        raise Exception(f"音声抽出中にエラーが発生しました: {e.stderr}")
    except Exception as e:
        raise Exception(f"文字起こし中にエラーが発生しました: {str(e)}")
    finally:
        # 一時ファイルの削除
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                print(f"一時ファイルの削除に失敗しました: {str(e)}")

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_video():
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('video')
        save_path = None

        if not file or file.filename == '':
            flash('ファイルが選択されていません')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('許可されていないファイル形式です')
            return redirect(request.url)

        try:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # 文字起こしの実行
            transcription = transcribe_video(save_path)
            
            # GCSにアップロード
            bucket_name = 'sns_application_ver2'
            gcs_path = f"videos/{filename}"
            gcs_url = upload_to_gcs(bucket_name, save_path, gcs_path)

            # Videoテーブルに保存
            new_video = Video(
                title=title,
                gcs_path=gcs_url,
                user_id=current_user.id,
                transcription=transcription
            )
            db.session.add(new_video)
            db.session.commit()

            flash('動画がアップロードされ、文字起こしが完了しました')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'エラーが発生しました: {str(e)}')
            return redirect(request.url)
        finally:
            # ローカルファイルを削除
            if save_path and os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception as e:
                    print(f"ローカルファイルの削除に失敗しました: {str(e)}")

    return render_template('upload.html')

@app.route('/videos')
def videos():
    search_query = request.args.get('search', '')
    
    if search_query:
        # タイトルと文字起こしの両方で検索
        videos = Video.query.filter(
            db.or_(
                Video.title.ilike(f'%{search_query}%'),
                Video.transcription.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        videos = Video.query.all()
    
    return render_template('videos.html', videos=videos)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)