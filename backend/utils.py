import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger("backend_utils")

def print_status(message: str, status: str = "INFO"):
    status_prefixes = {
        "INFO": "[*] INFO: ",
        "SUCCESS": "[+] SUCCESS: ",
        "WARNING": "[!] WARNING: ",
        "ERROR": "[-] ERROR: "
    }
    prefix = status_prefixes.get(status.upper(), "[*] INFO: ")
    print(f"{prefix}{message}")

def ensure_directory(directory_path: str) -> Path:
    path = Path(directory_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print_status(f"Created directory: {path.resolve()}", "INFO")
    return path

def validate_file_path(file_path: str) -> bool:
    path = Path(file_path)
    return path.exists() and path.is_file()

def read_csv_safe(file_path: str, **kwargs) -> pd.DataFrame:
    path = Path(file_path)
    if not validate_file_path(path):
        err_msg = f"File not found or invalid path: {path.resolve()}"
        print_status(err_msg, "ERROR")
        raise FileNotFoundError(err_msg)
    
    try:
        df = pd.read_csv(path, **kwargs)
        print_status(f"Successfully loaded file: {path.name} (Rows: {df.shape[0]}, Cols: {df.shape[1]})", "SUCCESS")
        return df
    except Exception as e:
        err_msg = f"Error reading CSV file '{path.name}': {str(e)}"
        print_status(err_msg, "ERROR")
        logger.error(err_msg, exc_info=True)
        raise e

def log_error(exception: Exception, context_message: str):
    err_msg = f"{context_message} | Error: {str(exception)}"
    print_status(err_msg, "ERROR")
    logger.error(err_msg, exc_info=True)

def report_missing_values(df: pd.DataFrame, name: str) -> dict:
    null_counts = df.isnull().sum().to_dict()
    total_nulls = sum(null_counts.values())
    
    print_status(f"Missing Values Report for {name} (Total rows: {df.shape[0]}):", "INFO")
    if total_nulls == 0:
        print("  -> No missing values found in any columns.")
    else:
        for col, val in null_counts.items():
            if val > 0:
                print(f"  -> Column '{col}': {val} missing values ({val/len(df)*100:.2f}%)")
    return null_counts

def report_duplicates(df: pd.DataFrame, name: str, subset: list = None) -> int:
    if subset:
        dup_count = int(df.duplicated(subset=subset).sum())
        subset_desc = f" (subset of columns: {subset})"
    else:
        dup_count = int(df.duplicated().sum())
        subset_desc = ""
        
    print_status(f"Duplicates Report for {name}: {dup_count} duplicate rows found{subset_desc}.", "INFO")
    return dup_count

def validate_dataset(df: pd.DataFrame, required_columns: list, name: str) -> bool:
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        err_msg = f"Validation Failed for {name}: Missing required columns: {missing_cols}"
        print_status(err_msg, "ERROR")
        logger.error(err_msg)
        raise KeyError(err_msg)
    
    print_status(f"Validation Passed for {name}: All required columns exist.", "SUCCESS")
    return True

def validate_column_types(df: pd.DataFrame, expected_types: dict, name: str) -> bool:
    passed = True
    print_status(f"Validating column types for {name}...", "INFO")
    for col, expected_type in expected_types.items():
        if col not in df.columns:
            continue
        
        col_type = str(df[col].dtype)
        if expected_type == 'int' and not col_type.startswith('int'):
            print_status(f"  Column '{col}' has type {col_type}, expected numeric integer.", "WARNING")
            passed = False
        elif expected_type == 'float' and not col_type.startswith('float'):
            print_status(f"  Column '{col}' has type {col_type}, expected numeric float.", "WARNING")
            passed = False
        elif expected_type == 'str' and not (col_type.startswith('object') or col_type.startswith('str')):
            print_status(f"  Column '{col}' has type {col_type}, expected string/object.", "WARNING")
            passed = False
            
    if passed:
        print_status(f"All columns in {name} match expected types.", "SUCCESS")
    else:
        print_status(f"Some type mismatches found in {name}.", "WARNING")
    return passed

def save_csv_safe(df: pd.DataFrame, file_path: str, name: str):
    path = Path(file_path)
    ensure_directory(path.parent)
    try:
        df.to_csv(path, index=False)
        print_status(f"Successfully saved clean {name} to: {path.resolve()}", "SUCCESS")
    except Exception as e:
        err_msg = f"Failed to save clean {name} to file '{path.name}': {str(e)}"
        print_status(err_msg, "ERROR")
        logger.error(err_msg, exc_info=True)
        raise e

def log_preprocessing(message: str):
    print_status(message, "INFO")
    logger.info(f"[PREPROCESSING] {message}")


def merge_datasets(app_df: pd.DataFrame, credit_df: pd.DataFrame, on_col: str = "ID") -> pd.DataFrame:
    log_preprocessing(f"Starting inner merge on column: '{on_col}'...")
    
    app_ids = set(app_df[on_col])
    credit_ids = set(credit_df[on_col])
    
    matched_ids = app_ids.intersection(credit_ids)
    unmatched_app = app_ids - credit_ids
    unmatched_credit = credit_ids - app_ids
    
    print_status(f"Merge Diagnostic Profile:", "INFO")
    print(f"  -> Total Unique Application IDs : {len(app_ids)}")
    print(f"  -> Total Unique Credit IDs      : {len(credit_ids)}")
    print(f"  -> Matched Overlapping IDs      : {len(matched_ids)}")
    print(f"  -> Unmatched Application IDs   : {len(unmatched_app)}")
    print(f"  -> Unmatched Credit IDs         : {len(unmatched_credit)}")
    
    merged_df = pd.merge(app_df, credit_df, on=on_col, how='inner')
    print_status(f"Merge complete. Final Dimensions: {merged_df.shape[0]} rows, {merged_df.shape[1]} columns.", "SUCCESS")
    
    return merged_df

def create_target_variable(credit_df: pd.DataFrame, status_col: str = "STATUS", target_col: str = "APPROVED") -> pd.DataFrame:
    log_preprocessing("Generating target variable from monthly credit history logs...")
    
    bad_statuses = {'1', '2', '3', '4', '5'}
    
    credit_df['IS_BAD_MONTH'] = np.where(credit_df[status_col].isin(bad_statuses), 1, 0)
    
    customer_risk = credit_df.groupby('ID')['IS_BAD_MONTH'].sum().reset_index()
    customer_risk[target_col] = np.where(customer_risk['IS_BAD_MONTH'] > 0, 0, 1)
    
    customer_risk = customer_risk.drop(columns=['IS_BAD_MONTH'])
    
    approved_count = customer_risk[target_col].value_counts().to_dict()
    approved_pct = customer_risk[target_col].value_counts(normalize=True).to_dict()
    
    print_status("Target Variable (APPROVED) distribution summary:", "INFO")
    print(f"  -> Approved (1) : {approved_count.get(1, 0)} ({approved_pct.get(1, 0.0)*100:.2f}%)")
    print(f"  -> Rejected (0) : {approved_count.get(0, 0)} ({approved_pct.get(0, 0.0)*100:.2f}%)")
    
    return customer_risk


def get_ist_time():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def datetime_to_ist_iso(dt) -> str:
    if not dt:
        return None
    from zoneinfo import ZoneInfo
    ist_tz = ZoneInfo("Asia/Kolkata")
    
    if isinstance(dt, str):
        from dateutil import parser
        try:
            dt = parser.parse(dt)
        except Exception:
            return dt
            
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        
    return dt.astimezone(ist_tz).isoformat()

