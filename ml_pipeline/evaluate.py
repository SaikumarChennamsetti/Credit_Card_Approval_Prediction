import sys
import os
import shutil
import time
from pathlib import Path
import joblib
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import (
    PROCESSED_DATA_PATH,
    MODELS_DIR,
    CANDIDATE_MODELS_DIR,
    MODEL_PATH,
    BEST_MODEL_METADATA_PATH,
    EVALUATION_REPORT_PATH,
    VISUALIZATIONS_DIR,
    TARGET_COL,
    TEST_SIZE,
    RANDOM_SEED,
    CV_FOLDS
)
from backend.utils import print_status, ensure_directory
from backend.services import (
    load_ml_dataset,
    calculate_classification_metrics,
    plot_evaluation_confusion_matrix,
    plot_evaluation_roc_curve,
    plot_evaluation_precision_recall_curve,
    plot_evaluation_feature_importance,
    generate_model_comparison_report,
    select_best_champion_model,
    evaluate_cross_validation_score
)

def run_model_evaluation_pipeline():
    print_status("Starting Model Evaluation & Selection pipeline...", "INFO")
    
    ensure_directory(VISUALIZATIONS_DIR)

    try:
        X, y = load_ml_dataset(str(PROCESSED_DATA_PATH), TARGET_COL)
    except Exception as e:
        print_status(f"Pipeline Terminated. Dataset loading failed: {str(e)}", "ERROR")
        return

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=TEST_SIZE, 
        random_state=RANDOM_SEED,
        stratify=y
    )

    candidate_files = list(CANDIDATE_MODELS_DIR.glob("*_candidate.joblib"))
    if not candidate_files:
        print_status(f"Pipeline Terminated. No candidate models found in: {CANDIDATE_MODELS_DIR.resolve()}", "ERROR")
        return
        
    print_status(f"Found {len(candidate_files)} candidate models to evaluate.", "INFO")
    
    results = []

    for model_path in candidate_files:
        algo_name = model_path.name.replace("_candidate.joblib", "")
        print("\n" + "-"*50)
        print(f"EVALUATING MODEL: {algo_name.upper()}")
        print("-"*50)
        
        try:
            model = joblib.load(model_path)
            
            start_pred = time.time()
            y_pred = model.predict(X_test)
            pred_time = (time.time() - start_pred) / len(X_test)
            
            if hasattr(model, "predict_proba"):
                y_prob = model.predict_proba(X_test)[:, 1]
            elif hasattr(model, "decision_function"):
                y_prob = model.decision_function(X_test)
            else:
                y_prob = y_pred
                
            metrics = calculate_classification_metrics(y_test, y_pred, y_prob)
            
            cv_score = evaluate_cross_validation_score(model, X_train, y_train, cv_folds=CV_FOLDS, random_seed=RANDOM_SEED)
            metrics['cv_score'] = float(cv_score)
            metrics['algorithm'] = algo_name
            metrics['prediction_latency_sec'] = pred_time
            
            plot_evaluation_confusion_matrix(
                y_test, y_pred, f"Confusion Matrix - {algo_name.upper()}", 
                VISUALIZATIONS_DIR / f"{algo_name}_confusion_matrix.png"
            )
            
            plot_evaluation_roc_curve(
                y_test, y_prob, f"ROC Curve - {algo_name.upper()}", 
                VISUALIZATIONS_DIR / f"{algo_name}_roc_curve.png"
            )
            
            plot_evaluation_precision_recall_curve(
                y_test, y_prob, f"Precision-Recall Curve - {algo_name.upper()}", 
                VISUALIZATIONS_DIR / f"{algo_name}_precision_recall_curve.png"
            )
            
            feature_names = X_test.columns.tolist()
            plot_evaluation_feature_importance(
                model, feature_names, f"Feature Importance - {algo_name.upper()}", 
                VISUALIZATIONS_DIR / f"{algo_name}_feature_importance.png"
            )
            
            print_status(f"Metrics: Accuracy: {metrics['accuracy']:.4f} | F1-Score: {metrics['f1_score']:.4f} | Recall: {metrics['recall']:.4f}", "SUCCESS")
            results.append(metrics)
            
        except Exception as e:
            print_status(f"Failed evaluating candidate model '{algo_name}': {str(e)}", "ERROR")

    comparison_df = generate_model_comparison_report(results, str(EVALUATION_REPORT_PATH))
    
    print("\n" + "="*80)
    print("MODEL COMPARISON TABLE (SORTED BY F1-SCORE)")
    print("="*80)
    print(comparison_df[['algorithm', 'accuracy', 'precision', 'recall', 'f1_score', 'roc_auc', 'cv_score']].to_string(index=False))
    print("="*80 + "\n")

    metadata = select_best_champion_model(comparison_df, MODELS_DIR)
    best_algo = metadata['best_algorithm']
    
    best_candidate_path = CANDIDATE_MODELS_DIR / f"{best_algo}_candidate.joblib"
    shutil.copy(best_candidate_path, MODEL_PATH)
    print_status(f"Saved production-ready champion model to: {MODEL_PATH.resolve()}", "SUCCESS")
    
    print("\n" + "="*80)
    print("EVALUATION & CHAMPION SELECTION SUMMARY")
    print("="*80)
    print(f"Selected Champion Model       : {best_algo.upper()}")
    print(f"Test Accuracy                 : {metadata['metrics']['accuracy']:.4f}")
    print(f"Test F1-Score                 : {metadata['metrics']['f1_score']:.4f}")
    print(f"Test Recall                   : {metadata['metrics']['recall']:.4f}")
    print(f"Comparison report saved to    : {EVALUATION_REPORT_PATH.resolve()}")
    print(f"Evaluation charts saved to    : {VISUALIZATIONS_DIR.resolve()}")
    print("="*80 + "\n")

if __name__ == '__main__':
    run_model_evaluation_pipeline()
