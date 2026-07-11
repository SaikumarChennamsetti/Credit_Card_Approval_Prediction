import sys
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import (
    CLEANED_APPLICATION_DATA_PATH,
    CLEANED_CREDIT_DATA_PATH,
    PROCESSED_DATA_PATH,
    PREPROCESSOR_PATH,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET_COL,
    RANDOM_SEED
)
from backend.utils import (
    read_csv_safe,
    save_csv_safe,
    merge_datasets,
    create_target_variable,
    log_preprocessing,
    print_status
)

def get_age_risk_score(age: float) -> float:
    if age <= 25:
        return 0.8
    elif age <= 40:
        return 0.4
    elif age <= 60:
        return 0.2
    else:
        return 0.5

def generate_synthetic_bias_correction_samples(n_cases=75):
    np.random.seed(RANDOM_SEED)
    synthetic_records = []
    
    for i in range(n_cases):
        synthetic_records.append({
            "CODE_GENDER": "M" if i % 2 == 0 else "F",
            "FLAG_OWN_CAR": "N",
            "FLAG_OWN_REALTY": "N",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": float(np.random.randint(0, 15000)),
            "NAME_INCOME_TYPE": "Unemployed" if i % 2 == 0 else "Student",
            "NAME_EDUCATION_TYPE": "Secondary / secondary special" if i % 2 == 0 else "Lower secondary",
            "NAME_FAMILY_STATUS": "Single / not married",
            "NAME_HOUSING_TYPE": "With parents",
            "DAYS_BIRTH": -int(np.random.randint(18*365.25, 23*365.25)),
            "DAYS_EMPLOYED": 365243,
            "FLAG_MOBIL": 1,
            "FLAG_WORK_PHONE": 0,
            "FLAG_PHONE": 1,
            "FLAG_EMAIL": 0,
            "OCCUPATION_TYPE": "Unspecified",
            "CNT_FAM_MEMBERS": 1,
            TARGET_COL: 0
        })
        
    for i in range(n_cases):
        synthetic_records.append({
            "CODE_GENDER": "M" if i % 2 == 0 else "F",
            "FLAG_OWN_CAR": "N",
            "FLAG_OWN_REALTY": "N",
            "CNT_CHILDREN": int(np.random.randint(3, 6)),
            "AMT_INCOME_TOTAL": float(np.random.randint(10000, 30000)),
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "DAYS_BIRTH": -int(np.random.randint(25*365.25, 45*365.25)),
            "DAYS_EMPLOYED": -int(np.random.randint(1*365.25, 5*365.25)),
            "FLAG_MOBIL": 1,
            "FLAG_WORK_PHONE": 1,
            "FLAG_PHONE": 0,
            "FLAG_EMAIL": 0,
            "OCCUPATION_TYPE": "Laborers",
            "CNT_FAM_MEMBERS": int(np.random.randint(5, 8)),
            TARGET_COL: 0
        })
        
    for i in range(n_cases):
        synthetic_records.append({
            "CODE_GENDER": "M" if i % 2 == 0 else "F",
            "FLAG_OWN_CAR": "N",
            "FLAG_OWN_REALTY": "N",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": float(np.random.randint(5000, 20000)),
            "NAME_INCOME_TYPE": "Pensioner",
            "NAME_EDUCATION_TYPE": "Secondary / secondary special",
            "NAME_FAMILY_STATUS": "Widow" if i % 2 == 0 else "Single / not married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "DAYS_BIRTH": -int(np.random.randint(65*365.25, 80*365.25)),
            "DAYS_EMPLOYED": 365243,
            "FLAG_MOBIL": 1,
            "FLAG_WORK_PHONE": 0,
            "FLAG_PHONE": 1,
            "FLAG_EMAIL": 0,
            "OCCUPATION_TYPE": "Unspecified",
            "CNT_FAM_MEMBERS": 1,
            TARGET_COL: 0
        })
        
    return pd.DataFrame(synthetic_records)

def build_preprocessing_pipeline(df: pd.DataFrame) -> tuple:
    log_preprocessing("Constructing scikit-learn preprocessing ColumnTransformer...")
    
    X = df.drop(columns=[TARGET_COL], errors='ignore')
    
    num_cols = [col for col in NUMERICAL_FEATURES if col in X.columns]
    cat_cols = [col for col in CATEGORICAL_FEATURES if col in X.columns]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False, drop='first'), cat_cols)
        ],
        remainder='drop'
    )
    
    X_transformed = preprocessor.fit_transform(X)
    
    cat_encoder = preprocessor.named_transformers_['cat']
    encoded_cat_cols = cat_encoder.get_feature_names_out(cat_cols).tolist()
    final_cols = num_cols + encoded_cat_cols
    
    X_processed = pd.DataFrame(X_transformed, columns=final_cols)
    
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print_status(f"Fitted preprocessor pipeline saved to: {PREPROCESSOR_PATH.resolve()}", "SUCCESS")
    
    return X_processed, preprocessor

def run_feature_engineering_pipeline():
    log_preprocessing("Starting Feature Engineering & Merge Pipeline...")
    
    try:
        app_df = read_csv_safe(CLEANED_APPLICATION_DATA_PATH)
        credit_df = read_csv_safe(CLEANED_CREDIT_DATA_PATH)
    except Exception as e:
        log_preprocessing(f"Failed to load cleaned datasets: {str(e)}")
        raise e
        
    orig_app_size = app_df.shape[0]
    
    customer_target = create_target_variable(credit_df, status_col="STATUS", target_col=TARGET_COL)
    
    merged_df = merge_datasets(app_df, customer_target, on_col="ID")
    
    log_preprocessing("Injecting synthetic negative risk samples to correct portfolio selection bias...")
    synthetic_df = generate_synthetic_bias_correction_samples(n_cases=75)
    merged_df = pd.concat([merged_df, synthetic_df], ignore_index=True)
    
    log_preprocessing("Engineering demographic and financial features...")
    merged_df['AGE'] = -merged_df['DAYS_BIRTH'] / 365.25
    merged_df['AGE_RISK_SCORE'] = merged_df['AGE'].apply(get_age_risk_score)
    merged_df['EMPLOYED_YEARS'] = np.where(merged_df['DAYS_EMPLOYED'] > 0, 0.0, -merged_df['DAYS_EMPLOYED'] / 365.25)
    merged_df['LOG_INCOME'] = np.log1p(merged_df['AMT_INCOME_TOTAL'])
    merged_df['INCOME_PER_MEMBER'] = merged_df['AMT_INCOME_TOTAL'] / merged_df['CNT_FAM_MEMBERS']
    
    merged_df['AGE_GROUP'] = pd.cut(
        merged_df['AGE'], 
        bins=[0, 25, 40, 60, 150], 
        labels=['18-25', '26-40', '41-60', '60+']
    ).astype(str)
    
    merged_df['INCOME_GROUP'] = pd.qcut(
        merged_df['AMT_INCOME_TOTAL'], 
        q=4, 
        labels=['Low-Income', 'Medium-Income', 'High-Income', 'Wealthy']
    ).astype(str)
    
    merged_df['FAMILY_SIZE_CAT'] = pd.cut(
        merged_df['CNT_FAM_MEMBERS'], 
        bins=[0, 2, 4, 100], 
        labels=['Small-Family', 'Medium-Family', 'Large-Family']
    ).astype(str)

    y_target = merged_df[TARGET_COL].values
    
    X_processed, preprocessor = build_preprocessing_pipeline(merged_df)
    
    processed_df = X_processed.copy()
    processed_df[TARGET_COL] = y_target
    
    save_csv_safe(processed_df, PROCESSED_DATA_PATH, "Final Processed ML Dataset")
    
    print("\n" + "="*80)
    print("FEATURE ENGINEERING & PREPROCESSING PIPELINE REPORT")
    print("="*80)
    print(f"Original Application Records  : {orig_app_size} rows")
    print(f"Final ML Dataset Dimensions   : {processed_df.shape[0]} rows, {processed_df.shape[1]} columns")
    print(f"Target distribution (APPROVED):")
    print(processed_df[TARGET_COL].value_counts().to_string())
    print("="*80 + "\n")

    return {
        "processed_df": processed_df,
        "preprocessor": preprocessor
    }

if __name__ == '__main__':
    run_feature_engineering_pipeline()
