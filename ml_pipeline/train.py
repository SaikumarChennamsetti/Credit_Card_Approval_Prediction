import sys
from pathlib import Path
import joblib
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import (
    PROCESSED_DATA_PATH,
    CANDIDATE_MODELS_DIR,
    TARGET_COL,
    TEST_SIZE,
    RANDOM_SEED,
    CV_FOLDS,
    HYPERPARAMETER_GRIDS
)
from backend.utils import print_status, ensure_directory
from backend.services import (
    load_ml_dataset,
    initialize_classifier,
    evaluate_cross_validation_score,
    tune_model_hyperparameters,
    generate_training_summary
)

def run_model_training_pipeline():
    print_status("Starting Machine Learning Model Training pipeline...", "INFO")
    
    ensure_directory(CANDIDATE_MODELS_DIR)

    try:
        X, y = load_ml_dataset(str(PROCESSED_DATA_PATH), TARGET_COL)
    except Exception as e:
        print_status(f"Pipeline Terminated. Dataset loading failed: {str(e)}", "ERROR")
        return

    if X.empty or len(y) == 0:
        print_status("Pipeline Terminated. Features matrix or targets array is empty.", "ERROR")
        return
        
    print_status(f"Successfully validated dataset. Predictors: {X.shape[1]} columns, Samples: {X.shape[0]} rows.", "SUCCESS")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=TEST_SIZE, 
        random_state=RANDOM_SEED,
        stratify=y
    )
    
    print_status(f"Dataset split complete (Test Size: {TEST_SIZE}):", "INFO")
    print(f"  -> Training Samples: {X_train.shape[0]}")
    print(f"  -> Testing Samples : {X_test.shape[0]}")

    summaries = []
    
    algorithms = list(HYPERPARAMETER_GRIDS.keys())
    print_status(f"Supported algorithms for training: {algorithms}", "INFO")
    
    for algo in algorithms:
        print("\n" + "="*60)
        print(f"TRAINING ALGORITHM: {algo.upper()}")
        print("="*60)
        
        try:
            base_model = initialize_classifier(algo, random_seed=RANDOM_SEED)
            
            param_grid = HYPERPARAMETER_GRIDS.get(algo, {})
            
            print_status(f"Evaluating base '{algo}' performance using cross-validation...", "INFO")
            evaluate_cross_validation_score(base_model, X_train, y_train, cv_folds=CV_FOLDS, random_seed=RANDOM_SEED)
            
            best_model, best_params, elapsed = tune_model_hyperparameters(
                algo, base_model, X_train, y_train, param_grid, cv_folds=CV_FOLDS, random_seed=RANDOM_SEED
            )
            
            print_status(f"Evaluating tuned '{algo}' performance using cross-validation...", "INFO")
            best_cv_score = evaluate_cross_validation_score(best_model, X_train, y_train, cv_folds=CV_FOLDS, random_seed=RANDOM_SEED)
            
            candidate_save_path = CANDIDATE_MODELS_DIR / f"{algo}_candidate.joblib"
            joblib.dump(best_model, candidate_save_path)
            print_status(f"Candidate model saved to: {candidate_save_path.name}", "SUCCESS")
            
            summary = generate_training_summary(algo, "SUCCESS", elapsed, best_cv_score, best_params)
            summaries.append(summary)
            
        except Exception as e:
            print_status(f"Failed training classifier algorithm '{algo}': {str(e)}", "ERROR")
            summary = generate_training_summary(algo, f"FAILED: {str(e)}", 0.0, 0.0, {})
            summaries.append(summary)

    print("\n" + "="*60)
    print("ALL MODELS TRAINING PIPELINE COMPLETED")
    print("="*60)
    print_status("Ready for Milestone 7 (Model Comparison & Champion Selection).", "SUCCESS")
    print("="*60 + "\n")

if __name__ == '__main__':
    run_model_training_pipeline()
