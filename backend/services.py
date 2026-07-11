import os
import time
import joblib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from backend.utils import print_status, ensure_directory, log_error

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    balanced_accuracy_score,
    matthews_corrcoef,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
    auc
)

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

from backend.models import db, PredictionHistory

sns.set_theme(style="darkgrid")
plt.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.titlesize': 16,
    'figure.facecolor': '#1e1e24',
    'axes.facecolor': '#2a2a35',
    'text.color': '#f5f5f7',
    'axes.labelcolor': '#f5f5f7',
    'xtick.color': '#f5f5f7',
    'ytick.color': '#f5f5f7',
    'grid.color': '#3f3f4f'
})

_MODEL = None
_PREPROCESSOR = None


def generate_summary_stats(df: pd.DataFrame) -> dict:
    summary = {}
    numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    summary['numerical_describe'] = df[numerical_cols].describe().to_dict()
    summary['categorical_describe'] = df[categorical_cols].describe().to_dict()
    summary['null_counts'] = df.isnull().sum().to_dict()
    summary['duplicate_count'] = int(df.duplicated().sum())
    summary['shape'] = df.shape
    return summary

def save_plot(fig, save_path: str):
    path = Path(save_path)
    ensure_directory(path.parent)
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1e1e24')
    plt.close(fig)
    print_status(f"Saved visualization to: {path.resolve()}", "SUCCESS")

def plot_missing_values(df: pd.DataFrame, name: str, save_path: str):
    null_counts = df.isnull().sum()
    null_percent = (null_counts / len(df)) * 100
    
    if null_counts.sum() == 0:
        print_status(f"No missing values in {name}. Skipping missing value plot.", "INFO")
        return
    
    missing_df = pd.DataFrame({'Counts': null_counts, 'Percentage': null_percent})
    missing_df = missing_df[missing_df['Counts'] > 0].sort_values(by='Counts', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(x=missing_df.index, y=missing_df['Counts'], ax=ax, palette="viridis")
    ax.set_title(f"Missing Value Counts - {name}", pad=15)
    ax.set_ylabel("Count")
    ax.set_xlabel("Columns")
    plt.xticks(rotation=45)
    
    for i, v in enumerate(missing_df['Counts']):
        ax.text(i, v + (v * 0.01), f"{int(v)} ({missing_df['Percentage'].iloc[i]:.1f}%)", 
                ha='center', va='bottom', color='#f5f5f7', fontsize=9)
        
    save_plot(fig, save_path)

def plot_correlation_heatmap(df: pd.DataFrame, name: str, save_path: str):
    numerical_df = df.select_dtypes(include=[np.number]).drop(columns=['ID'], errors='ignore')
    if numerical_df.shape[1] < 2:
        print_status(f"Not enough numerical columns in {name} to compute correlation.", "INFO")
        return
        
    corr = numerical_df.corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, 
                ax=ax, cbar_kws={"shrink": .8}, square=True, linewidths=.5)
    ax.set_title(f"Correlation Heatmap - {name}", pad=20)
    save_plot(fig, save_path)

def plot_distribution(df: pd.DataFrame, col: str, title: str, save_path: str, plot_type: str = "hist", bins: int = 30):
    if col not in df.columns:
        print_status(f"Column '{col}' not found in dataframe. Skipping distribution.", "WARNING")
        return
        
    fig, ax = plt.subplots(figsize=(10, 5))
    
    if plot_type == "hist":
        sns.histplot(data=df, x=col, kde=True, bins=bins, ax=ax, color="#4c6ef5")
        ax.set_ylabel("Frequency")
    elif plot_type == "count":
        order = df[col].value_counts().index
        sns.countplot(data=df, x=col, order=order, ax=ax, palette="plasma")
        ax.set_ylabel("Count")
        plt.xticks(rotation=45)
    
    ax.set_title(title, pad=15)
    ax.set_xlabel(col)
    
    save_plot(fig, save_path)


def load_ml_dataset(processed_data_path: str, target_col: str) -> tuple:
    print_status(f"Loading preprocessed ML dataset: {processed_data_path}", "INFO")
    try:
        df = pd.read_csv(processed_data_path)
    except Exception as e:
        log_error(e, f"Failed to load processed dataset: {processed_data_path}")
        raise e
        
    if target_col not in df.columns:
        err_msg = f"Critical Target variable '{target_col}' not found in final dataset columns."
        print_status(err_msg, "ERROR")
        raise KeyError(err_msg)
        
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y

def initialize_classifier(algorithm: str, random_seed: int = 42):
    algorithm_clean = algorithm.lower().strip()
    
    if algorithm_clean == 'logistic_regression':
        return LogisticRegression(random_state=random_seed, max_iter=1000, class_weight='balanced')
    elif algorithm_clean == 'decision_tree':
        return DecisionTreeClassifier(random_state=random_seed, class_weight='balanced')
    elif algorithm_clean == 'random_forest':
        return RandomForestClassifier(random_state=random_seed, class_weight='balanced')
    elif algorithm_clean == 'svm':
        return SVC(random_state=random_seed, probability=True, class_weight='balanced')
    elif algorithm_clean == 'knn':
        return KNeighborsClassifier()
    elif algorithm_clean == 'naive_bayes':
        return GaussianNB()
    elif algorithm_clean == 'gradient_boosting':
        return GradientBoostingClassifier(random_state=random_seed)
    elif algorithm_clean == 'xgboost':
        if HAS_XGB:
            return XGBClassifier(random_state=random_seed, use_label_encoder=False)
        else:
            print_status("XGBoost package not available. Falling back to GradientBoostingClassifier.", "WARNING")
            return GradientBoostingClassifier(random_state=random_seed)
    else:
        raise ValueError(f"Unsupported algorithm type: '{algorithm}'")

def evaluate_cross_validation_score(model, X_train: pd.DataFrame, y_train: pd.Series, cv_folds: int = 5, random_seed: int = 42) -> float:
    kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_seed)
    scores = cross_val_score(model, X_train, y_train, cv=kfold, scoring='accuracy')
    mean_score = scores.mean()
    return mean_score

def tune_model_hyperparameters(algorithm: str, base_model, X_train: pd.DataFrame, y_train: pd.Series, param_grid: dict, cv_folds: int = 5, random_seed: int = 42):
    if not param_grid:
        start_time = time.time()
        base_model.fit(X_train, y_train)
        elapsed = time.time() - start_time
        return base_model, {}, elapsed
        
    kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=random_seed)
    grid_search = GridSearchCV(estimator=base_model, param_grid=param_grid, cv=kfold, scoring='accuracy', n_jobs=-1)
    
    start_time = time.time()
    grid_search.fit(X_train, y_train)
    elapsed = time.time() - start_time
    
    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_score = grid_search.best_score_
    
    return best_model, best_params, elapsed

def generate_training_summary(algorithm: str, status: str, elapsed_time: float, cv_score: float, best_params: dict) -> dict:
    summary = {
        "algorithm": algorithm,
        "status": status,
        "elapsed_time_sec": elapsed_time,
        "cross_validation_score": cv_score,
        "best_params": best_params
    }
    return summary

def calculate_classification_metrics(y_true: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray = None) -> dict:
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred))
    }
    
    if y_prob is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        except Exception:
            metrics["roc_auc"] = 0.5
    else:
        metrics["roc_auc"] = 0.5
        
    return metrics

def plot_evaluation_confusion_matrix(y_true: pd.Series, y_pred: np.ndarray, title: str, save_path: str):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax, cbar=False,
                xticklabels=["Rejected (0)", "Approved (1)"],
                yticklabels=["Rejected (0)", "Approved (1)"])
    ax.set_title(title, pad=15)
    ax.set_ylabel("True Status")
    ax.set_xlabel("Predicted Status")
    save_plot(fig, save_path)

def plot_evaluation_roc_curve(y_true: pd.Series, y_prob: np.ndarray, title: str, save_path: str):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color='#4c6ef5', lw=2, label=f"ROC Curve (AUC = {roc_auc:.4f})")
    ax.plot([0, 1], [0, 1], color='#fa5252', lw=1, linestyle='--')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(title, pad=15)
    ax.legend(loc="lower right")
    save_plot(fig, save_path)

def plot_evaluation_precision_recall_curve(y_true: pd.Series, y_prob: np.ndarray, title: str, save_path: str):
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, color='#12b886', lw=2, label=f"PR Curve (AUC = {pr_auc:.4f})")
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    ax.set_title(title, pad=15)
    ax.legend(loc="lower left")
    save_plot(fig, save_path)

def plot_evaluation_feature_importance(model, feature_names: list, title: str, save_path: str):
    if not hasattr(model, 'feature_importances_'):
        print_status(f"Model of type {type(model)} does not support feature importances. Skipping.", "INFO")
        return
        
    importances = model.feature_importances_
    if len(importances) != len(feature_names):
        feature_names = [f"Feature_{i}" for i in range(len(importances))]
        
    feat_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False).head(15)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x='Importance', y='Feature', data=feat_df, ax=ax, palette="mako")
    ax.set_title(title, pad=15)
    ax.set_xlabel('Relative Importance')
    save_plot(fig, save_path)

def generate_model_comparison_report(results: list, report_save_path: str) -> pd.DataFrame:
    df = pd.DataFrame(results)
    df = df.sort_values(by='f1_score', ascending=False)
    
    path = Path(report_save_path)
    ensure_directory(path.parent)
    df.to_csv(path, index=False)
    print_status(f"Successfully saved comparison report CSV to: {path.resolve()}", "SUCCESS")
    
    return df

def select_best_champion_model(comparison_df: pd.DataFrame, models_dir: Path) -> dict:
    if comparison_df.empty:
        raise ValueError("Cannot select model from empty comparison summary table.")
        
    best_row = comparison_df.iloc[0].to_dict()
    best_algo = best_row['algorithm']
    
    print_status(f"Champion Selection Process: Selected '{best_algo}' as the Best Production Model.", "SUCCESS")
    
    metadata = {
        "best_algorithm": best_algo,
        "metrics": {
            "accuracy": float(best_row['accuracy']),
            "precision": float(best_row['precision']),
            "recall": float(best_row['recall']),
            "f1_score": float(best_row['f1_score']),
            "roc_auc": float(best_row['roc_auc']),
            "cv_score": float(best_row['cv_score'])
        },
        "selected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rationale": (
            f"The '{best_algo}' model achieved the highest F1 score ({best_row['f1_score']:.4f}) and "
            f"best recall ({best_row['recall']:.4f}) on the unseen test dataset, ensuring optimal "
            f"balance between credit approvals and default risk controls."
        )
    }
    
    metadata_path = Path(models_dir) / 'best_model_metadata.json'
    ensure_directory(metadata_path.parent)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print_status(f"Champion metadata written to: {metadata_path.resolve()}", "SUCCESS")
    return metadata


def load_production_model_assets(model_path: str, preprocessor_path: str) -> bool:
    global _MODEL, _PREPROCESSOR
    
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
            
    def safe_print(msg: str):
        try:
            print(msg)
        except UnicodeEncodeError:
            try:
                print(msg.replace("✓", "[ok]"))
            except Exception:
                pass
    
    m_path = Path(model_path)
    p_path = Path(preprocessor_path)
    
    # 1. Load ML Model
    safe_print("✓ Loading ML model...")
    if not (m_path.exists() and m_path.is_file()):
        err_msg = f"Model weights file missing: {m_path.resolve()}"
        safe_print(f"Error: Model weights file missing at {m_path.resolve()}")
        raise FileNotFoundError(err_msg)
        
    try:
        _MODEL = joblib.load(m_path)
        safe_print("✓ Model loaded successfully.")
    except Exception as e:
        safe_print(f"Error loading model from {m_path.resolve()}: {str(e)}")
        import traceback
        traceback.print_exc()
        log_error(e, f"Failed loading Joblib model weights from path: {m_path.resolve()}")
        raise e

    # 2. Load Preprocessor
    safe_print("✓ Loading preprocessor...")
    if not (p_path.exists() and p_path.is_file()):
        err_msg = f"Preprocessor transformer pipeline file missing: {p_path.resolve()}"
        safe_print(f"Error: Preprocessor transformer pipeline file missing at {p_path.resolve()}")
        raise FileNotFoundError(err_msg)
        
    try:
        _PREPROCESSOR = joblib.load(p_path)
        safe_print("✓ Preprocessor loaded successfully.")
    except Exception as e:
        safe_print(f"Error loading preprocessor from {p_path.resolve()}: {str(e)}")
        import traceback
        traceback.print_exc()
        log_error(e, f"Failed loading Joblib preprocessor from path: {p_path.resolve()}")
        raise e

    safe_print("✓ Prediction service initialized.")
    return True


def validate_prediction_input(data: dict) -> list:
    validation_errors = []
    
    required_fields = {
        'CODE_GENDER': str,
        'FLAG_OWN_CAR': str,
        'FLAG_OWN_REALTY': str,
        'CNT_CHILDREN': int,
        'AMT_INCOME_TOTAL': (int, float),
        'NAME_INCOME_TYPE': str,
        'NAME_EDUCATION_TYPE': str,
        'NAME_FAMILY_STATUS': str,
        'NAME_HOUSING_TYPE': str,
        'AGE': (int, float),
        'EMPLOYED_YEARS': (int, float),
        'OCCUPATION_TYPE': str,
        'CNT_FAM_MEMBERS': int
    }
    
    for field, field_type in required_fields.items():
        if field not in data:
            validation_errors.append(f"Missing required field: '{field}'")
            continue
            
        val = data[field]
        if not isinstance(val, field_type):
            validation_errors.append(f"Invalid type for '{field}'. Expected {field_type}, received {type(val)}")
            
    if not validation_errors:
        if data['CODE_GENDER'].upper() not in {'M', 'F'}:
            validation_errors.append("CODE_GENDER must be 'M' or 'F'")
        if data['FLAG_OWN_CAR'].upper() not in {'Y', 'N'}:
            validation_errors.append("FLAG_OWN_CAR must be 'Y' or 'N'")
        if data['FLAG_OWN_REALTY'].upper() not in {'Y', 'N'}:
            validation_errors.append("FLAG_OWN_REALTY must be 'Y' or 'N'")
        if data['CNT_CHILDREN'] < 0:
            validation_errors.append("CNT_CHILDREN cannot be negative")
        if data['AMT_INCOME_TOTAL'] <= 0:
            validation_errors.append("AMT_INCOME_TOTAL must be positive")
        if data['AGE'] < 18 or data['AGE'] > 120:
            validation_errors.append("AGE must be between 18 and 120")
        if data['EMPLOYED_YEARS'] < 0:
            validation_errors.append("EMPLOYED_YEARS cannot be negative")
        if data['CNT_FAM_MEMBERS'] < 1:
            validation_errors.append("CNT_FAM_MEMBERS must be at least 1")
            
    return validation_errors

def execute_prediction(raw_input: dict) -> dict:
    global _MODEL, _PREPROCESSOR
    if _MODEL is None or _PREPROCESSOR is None:
        raise RuntimeError("The machine learning model could not be loaded. Please check the model files, configuration paths, and startup logs.")
        
    input_data = raw_input.copy()
    
    input_data['CODE_GENDER'] = input_data['CODE_GENDER'].upper()
    input_data['FLAG_OWN_CAR'] = input_data['FLAG_OWN_CAR'].upper()
    input_data['FLAG_OWN_REALTY'] = input_data['FLAG_OWN_REALTY'].upper()
    
    input_data['INCOME_PER_MEMBER'] = float(input_data['AMT_INCOME_TOTAL'] / input_data['CNT_FAM_MEMBERS'])
    input_data['LOG_INCOME'] = float(np.log1p(input_data['AMT_INCOME_TOTAL']))
    
    age = input_data['AGE']
    
    if age <= 25:
        input_data['AGE_RISK_SCORE'] = 0.8
        age_grp = '18-25'
    elif age <= 40:
        input_data['AGE_RISK_SCORE'] = 0.4
        age_grp = '26-40'
    elif age <= 60:
        input_data['AGE_RISK_SCORE'] = 0.2
        age_grp = '41-60'
    else:
        input_data['AGE_RISK_SCORE'] = 0.5
        age_grp = '60+'
        
    input_data['AGE_GROUP'] = age_grp
        
    inc = input_data['AMT_INCOME_TOTAL']
    if inc < 135000:
        inc_grp = 'Low-Income'
    elif inc < 180000:
        inc_grp = 'Medium-Income'
    elif inc < 225000:
        inc_grp = 'High-Income'
    else:
        inc_grp = 'Wealthy'
    input_data['INCOME_GROUP'] = inc_grp
        
    fam = input_data['CNT_FAM_MEMBERS']
    if fam <= 2:
        fam_grp = 'Small-Family'
    elif fam <= 4:
        fam_grp = 'Medium-Family'
    else:
        fam_grp = 'Large-Family'
    input_data['FAMILY_SIZE_CAT'] = fam_grp
    
    df_raw = pd.DataFrame([input_data])
    
    try:
        X_processed = _PREPROCESSOR.transform(df_raw)
        
        if hasattr(_MODEL, "predict_proba"):
            probs = _MODEL.predict_proba(X_processed)[0]
            probability = float(probs[1])
        else:
            probability = 1.0 if int(_MODEL.predict(X_processed)[0]) == 1 else 0.0
            
        y_pred = 1 if probability >= 0.5 else 0
        confidence = float(probs[y_pred]) if hasattr(_MODEL, "predict_proba") else 1.0
            
        if probability >= 0.8:
            risk_level = "Low"
        elif probability >= 0.5:
            risk_level = "Medium"
        else:
            risk_level = "High"
            
        is_approved = (y_pred == 1)
        explanation = ""
        suggestions = []
        
        if is_approved:
            explanation = "Your application exhibits strong income stability and a low risk profile."
            suggestions = ["Maintain your steady income stream and continue paying off existing debts on time."]
        else:
            explanation = "Your application was rejected due to a higher default risk rating."
            
            if input_data['EMPLOYED_YEARS'] < 1.0:
                suggestions.append("Increase your continuous employment tenure to at least 1 year to show stability.")
            if input_data['INCOME_PER_MEMBER'] < 40000:
                suggestions.append("Consider reducing financial dependencies or applying with a co-signer to improve income-per-member stats.")
            if input_data['AMT_INCOME_TOTAL'] < 100000:
                suggestions.append("Apply for a lower-limit credit card or build credit history with micro-loans.")
            if not suggestions:
                suggestions.append("Review your debt-to-income ratio and ensure all historical accounts are fully paid up.")
                
        return {
            "approved": is_approved,
            "probability": probability,
            "confidence_score": confidence,
            "risk_level": risk_level,
            "explanation": explanation,
            "suggestions": suggestions
        }
    except Exception as e:
        log_error(e, "Error executing model prediction inference.")
        raise e


def save_prediction_record(raw_input: dict, prediction_results: dict, user_id: str, model_version: str = "1.0.0") -> int:
    print_status("Saving prediction record to database...", "INFO")
    
    applicant_id = raw_input.get('applicant_id')
    
    try:
        record = PredictionHistory(
            user_id=user_id,
            applicant_id=applicant_id,
            prediction_result=1 if prediction_results['approved'] else 0,
            approval_probability=prediction_results['probability'],
            confidence_score=prediction_results['confidence_score'],
            explanation=prediction_results['explanation'],
            customer_input=raw_input,
            model_version=model_version
        )
        db.session.add(record)
        db.session.commit()
        print_status(f"Prediction saved successfully. Record ID: {record.id}", "SUCCESS")
        return record.id
    except Exception as e:
        db.session.rollback()
        log_error(e, "Failed to save prediction record to database.")
        raise e

def retrieve_prediction_history(user_id: str, page: int = 1, per_page: int = 10, sort_by: str = "created_at", sort_order: str = "desc", filters: dict = None) -> tuple:
    print_status(f"Querying prediction history for user {user_id} (Page: {page}, PerPage: {per_page}, SortBy: {sort_by}, Order: {sort_order})...", "INFO")
    
    query = PredictionHistory.query.filter(PredictionHistory.user_id == user_id)
    
    if filters:
        if 'prediction_result' in filters and filters['prediction_result'] is not None:
            query = query.filter(PredictionHistory.prediction_result == int(filters['prediction_result']))
        if 'applicant_id' in filters and filters['applicant_id']:
            query = query.filter(PredictionHistory.applicant_id == str(filters['applicant_id']))
        if 'risk_level' in filters and filters['risk_level']:
            risk = filters['risk_level'].lower()
            if risk == "low":
                query = query.filter(PredictionHistory.approval_probability >= 0.8)
            elif risk == "medium":
                query = query.filter(PredictionHistory.approval_probability >= 0.5, PredictionHistory.approval_probability < 0.8)
            elif risk == "high":
                query = query.filter(PredictionHistory.approval_probability < 0.5)

    if hasattr(PredictionHistory, sort_by):
        sort_column = getattr(PredictionHistory, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(PredictionHistory.created_at.desc())
        
    try:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        records = [record.to_dict() for record in pagination.items]
        print_status(f"History retrieved successfully. Match count: {pagination.total}", "SUCCESS")
        return records, pagination.total, pagination.pages
    except Exception as e:
        log_error(e, "Failed to query prediction history from database.")
        raise e

def retrieve_prediction_by_id(record_id: int, user_id: str) -> dict:
    print_status(f"Retrieving prediction record by ID: {record_id} for user: {user_id}...", "INFO")
    try:
        record = db.session.get(PredictionHistory, record_id)
        if record and record.user_id == user_id:
            return record.to_dict()
        return None
    except Exception as e:
        log_error(e, f"Failed to retrieve record ID: {record_id}")
        raise e

def delete_prediction_by_id(record_id: int, user_id: str) -> bool:
    print_status(f"Deleting prediction record by ID: {record_id} for user: {user_id}...", "INFO")
    try:
        record = db.session.get(PredictionHistory, record_id)
        if record and record.user_id == user_id:
            db.session.delete(record)
            db.session.commit()
            print_status(f"Record deleted successfully. ID: {record_id}", "SUCCESS")
            return True
        print_status(f"Record delete failed. ID {record_id} not found or unauthorized.", "WARNING")
        return False
    except Exception as e:
        db.session.rollback()
        log_error(e, f"Failed to delete record ID: {record_id}")
        raise e


def save_contact_message(full_name: str, email: str, subject: str, message: str, user_id: str = None) -> dict:
    from backend.models import ContactMessage
    import re

    full_name = full_name.strip() if full_name else ""
    email = email.strip() if email else ""
    subject = subject.strip() if subject else ""
    message = message.strip() if message else ""

    if not full_name:
        raise ValueError("Full Name is required.")
    if not email:
        raise ValueError("Email Address is required.")
    if not subject:
        raise ValueError("Subject is required.")
    if not message:
        raise ValueError("Message is required.")

    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        raise ValueError("Please provide a valid email address.")

    try:
        new_msg = ContactMessage(
            user_id=user_id,
            full_name=full_name,
            email=email,
            subject=subject,
            message=message
        )
        db.session.add(new_msg)
        db.session.commit()
        print_status(f"Saved contact message from {email} with ID: {new_msg.id}", "SUCCESS")
        return new_msg.to_dict()
    except Exception as e:
        db.session.rollback()
        log_error(e, "Failed to save contact message to database.")
        raise e

