import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key_change_in_production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
    
    DATABASE_URL_RAW = os.getenv('DATABASE_URL', 'sqlite:///db/database.db')
    if DATABASE_URL_RAW.startswith('sqlite:///'):
        db_relative_path = DATABASE_URL_RAW.replace('sqlite:///', '')
        db_absolute_path = BASE_DIR / db_relative_path
        db_absolute_path.parent.mkdir(parents=True, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_absolute_path.as_posix()}"
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL_RAW
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'data' / 'uploads'))
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    raw_model_path = os.getenv('MODEL_PATH')
    if raw_model_path:
        path_obj = Path(raw_model_path)
        MODEL_PATH = str(BASE_DIR / path_obj if not path_obj.is_absolute() else path_obj)
    else:
        MODEL_PATH = str(BASE_DIR / 'models' / 'best_model.joblib')

    raw_preprocessor_path = os.getenv('PREPROCESSOR_PATH')
    if raw_preprocessor_path:
        path_obj = Path(raw_preprocessor_path)
        PREPROCESSOR_PATH = str(BASE_DIR / path_obj if not path_obj.is_absolute() else path_obj)
    else:
        PREPROCESSOR_PATH = str(BASE_DIR / 'models' / 'preprocessor.joblib')


    DATA_DIR = BASE_DIR / 'data'
    APPLICATION_DATA_PATH = DATA_DIR / 'application_record.csv'
    CREDIT_DATA_PATH = DATA_DIR / 'credit_record.csv'
    PROCESSED_DATA_PATH = DATA_DIR / 'processed_data.csv'

    LOG_DIR = BASE_DIR / 'logs'
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_FILE_PATH = str(LOG_DIR / 'app.log')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
