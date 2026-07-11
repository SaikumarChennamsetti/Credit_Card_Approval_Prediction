import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)

RANDOM_SEED = int(os.getenv('RANDOM_SEED', 42))

TEST_SIZE = float(os.getenv('TEST_SIZE', 0.2))

TARGET_COL = 'APPROVED'

DATA_DIR = BASE_DIR / 'data'
APPLICATION_DATA_PATH = DATA_DIR / 'application_record.csv'
CREDIT_DATA_PATH = DATA_DIR / 'credit_record.csv'
CLEANED_APPLICATION_DATA_PATH = DATA_DIR / 'application_record_cleaned.csv'
CLEANED_CREDIT_DATA_PATH = DATA_DIR / 'credit_record_cleaned.csv'
PROCESSED_DATA_PATH = DATA_DIR / 'processed_data.csv'

MODELS_DIR = BASE_DIR / 'models'
MODEL_PATH = MODELS_DIR / 'best_model.joblib'
PREPROCESSOR_PATH = MODELS_DIR / 'preprocessor.joblib'
CANDIDATE_MODELS_DIR = MODELS_DIR / 'candidates'
BEST_MODEL_METADATA_PATH = MODELS_DIR / 'best_model_metadata.json'

REPORTS_DIR = BASE_DIR / 'reports'
VISUALIZATIONS_DIR = REPORTS_DIR / 'visualizations'
EVALUATION_REPORT_PATH = REPORTS_DIR / 'model_comparison_report.csv'

DATABASE_URL_RAW = os.getenv('DATABASE_URL', 'sqlite:///db/database.db')
if DATABASE_URL_RAW.startswith('sqlite:///'):
    db_relative_path = DATABASE_URL_RAW.replace('sqlite:///', '')
    db_absolute_path = BASE_DIR / db_relative_path
    DATABASE_URL = f"sqlite:///{db_absolute_path.as_posix()}"
else:
    DATABASE_URL = DATABASE_URL_RAW

LOGS_DIR = BASE_DIR / 'logs'
LOG_FILE_PATH = LOGS_DIR / 'app.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

CATEGORICAL_FEATURES = [
    'CODE_GENDER', 
    'FLAG_OWN_CAR', 
    'FLAG_OWN_REALTY', 
    'NAME_INCOME_TYPE', 
    'NAME_EDUCATION_TYPE', 
    'NAME_FAMILY_STATUS', 
    'NAME_HOUSING_TYPE', 
    'OCCUPATION_TYPE',
    'AGE_GROUP',
    'INCOME_GROUP',
    'FAMILY_SIZE_CAT'
]

NUMERICAL_FEATURES = [
    'LOG_INCOME', 
    'AGE', 
    'AGE_RISK_SCORE',
    'EMPLOYED_YEARS', 
    'INCOME_PER_MEMBER',
    'CNT_CHILDREN',
    'CNT_FAM_MEMBERS'
]

CV_FOLDS = int(os.getenv('CV_FOLDS', 5))

HYPERPARAMETER_GRIDS = {
    'logistic_regression': {
        'C': [0.01, 0.1, 1.0, 10.0],
        'solver': ['liblinear', 'lbfgs']
    },
    'decision_tree': {
        'max_depth': [3, 5, 10, None],
        'min_samples_split': [2, 5, 10]
    },
    'random_forest': {
        'n_estimators': [50, 100, 200],
        'max_depth': [5, 10, None],
        'min_samples_split': [2, 5]
    },
    'svm': {
        'C': [0.1, 1.0, 10.0],
        'kernel': ['linear', 'rbf']
    },
    'knn': {
        'n_neighbors': [3, 5, 7, 9],
        'weights': ['uniform', 'distance']
    },
    'naive_bayes': {},
    'gradient_boosting': {
        'n_estimators': [50, 100],
        'learning_rate': [0.01, 0.1, 0.2],
        'max_depth': [3, 5]
    },
    'xgboost': {
        'n_estimators': [50, 100],
        'learning_rate': [0.01, 0.1, 0.2],
        'max_depth': [3, 5],
        'eval_metric': ['logloss']
    }
}

EVALUATION_METRICS = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc', 'balanced_accuracy', 'mcc']

for path in [DATA_DIR, MODELS_DIR, CANDIDATE_MODELS_DIR, REPORTS_DIR, VISUALIZATIONS_DIR, LOGS_DIR]:
    path.mkdir(parents=True, exist_ok=True)
