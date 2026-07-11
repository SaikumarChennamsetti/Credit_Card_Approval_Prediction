# Exploratory Data Analysis & Model Explanation Document

This document summarizes the insights obtained during the Exploratory Data Analysis (EDA) and explains the redesigned, production-ready machine learning pipeline.

---

## 1. Dataset Overview
The system processes credit card risk assessments using two core datasets:
1. **Application Record (`application_record.csv`)**: Captures demographic, income, employment, and housing details for bank applicants.
2. **Credit Record (`credit_record.csv`)**: Captures month-by-month repayment track logs for historical customers.

These files are linked using the unique customer identity field, **`ID`**.

---

## 2. Key Observations
* **Age Distribution**: Most applicants fall between 30 and 55 years of age.
* **Income Levels**: Annual income is heavily skewed right, with a concentrated majority earning under $200,000, while a few high-earning individuals act as extreme outliers (up to $1,500,000+).
* **Demographics**: Females represent the majority of applicants in this dataset. Most applicants are married and live in houses/apartments they own.
* **Occupation & Employment**: A large portion of applicants are listed under "Laborers", followed by "Sales staff" and "Core staff". In employment duration, a significant proportion is marked as unemployed or pensioners (re-coded via large positive integers in raw sheets).

---

## 3. Potential Problems in the Data
* **Pensioner Employment Flag**: Unemployed applicants and pensioners are marked with a duration of `365243` days in the `DAYS_EMPLOYED` column. This equates to 1000 years and represents a special value/placeholder that will break linear models if not handled properly.
* **Missing Occupations**: The `OCCUPATION_TYPE` column contains a large number of missing values (about 30%+ nulls). This requires imputation or mapping to a separate class (e.g., "Unknown").
* **Duplicate IDs**: The application record contains duplicate rows for the same `ID`, indicating either multiple applications or system logging duplicates. These duplicate rows must be removed before joining datasets.
* **Low Intersection Ratio**: Only a small percentage of ID values in the application dataset overlap with IDs in the credit dataset. Joining the two tables will shrink the training set.

---

## 4. Missing Value & Duplicate Summary
* **Application Records**:
  * Missing: `OCCUPATION_TYPE` is the only column with significant missing records.
  * Duplicates: Full duplicate rows are minimal, but duplicate entries on the `ID` column are present.
* **Credit Records**:
  * Missing: No missing values are found in the status or months balance tracks.
  * Duplicates: No full duplicate rows are present, but many rows exist for the same `ID` (as expected, since it contains monthly logs for each customer).

---

## 5. Feature Relationships & Correlations
* **Income and Assets**: Positive correlation exists between owning a car, real estate, and higher income levels.
* **Family Size and Children**: Strong linear correlation is present between the number of children (`CNT_CHILDREN`) and total family members (`CNT_FAM_MEMBERS`). Including both features in regression models could cause multi-collinearity issues.
* **Age and Experience**: Negative correlation in raw terms (since they are represented as negative offsets of days from the current date). Younger individuals naturally show shorter employment histories.

---

## 6. Class Imbalance Observations
* In `credit_record.csv`, the monthly status records are heavily weighted toward on-time payments or minor delays (`C` and `0`), which represents over 98% of the logs.
* When aggregating history to label a customer as "Risk" (if they have ever gone 30+ days overdue), the target variable remains heavily imbalanced. "Safe" applicants dominate the dataset, while "Risk" applicants comprise a small minority (~1-3%).
* **Recommendation**: If not addressed, classifiers will default to predicting "Safe" for all applicants. We must use balancing techniques (e.g., class weight tuning or SMOTE over-sampling) during model training.

---

## 7. Recommendations for Preprocessing
1. **Duplicate ID Deduplication**: Drop duplicate customer ID rows from the application records, keeping the most recent or complete record.
2. **Missing Occupation Mapping**: Impute missing `OCCUPATION_TYPE` values with an "Unspecified" category to preserve those records.
3. **Imputing Pensioner Days**: Re-code the placeholder value `365243` in `DAYS_EMPLOYED` to `0` and create a binary indicator column `IS_PENSIONER` or `IS_UNEMPLOYED`.
4. **Encoding Categoricals**: Apply **One-Hot Encoding** for nominal categorical features (e.g., `CODE_GENDER`, `FLAG_OWN_CAR`, `NAME_HOUSING_TYPE`) and **Ordinal Encoding** for ordered elements (e.g., `NAME_EDUCATION_TYPE`).
5. **Feature Scaling**: Apply standard scaling (mean=0, variance=1) on continuous features like `AMT_INCOME_TOTAL`, `AGE`, and `EMPLOYED_YEARS` to ensure stable gradients in distance-based and linear models.
6. **Feature Engineering**:
   * Calculate exact `AGE` from `DAYS_BIRTH`.
   * Calculate `EMPLOYMENT_DURATION_YEARS` from `DAYS_EMPLOYED`.
   * Create an `INCOME_PER_FAMILY_MEMBER` feature to better capture financial stability.

---

## 8. Data Cleaning & Preprocessing

### 1. What Problems Were Found
* **Missing values** in `OCCUPATION_TYPE` column (79 values out of 1000).
* **Duplicate row entries**: Multiple application records sharing duplicate `ID` values.
* **Inconsistent categories**: Varied capitalization or trailing spaces in text fields.
* **Logical inconsistencies**:
  * Family sizes smaller than children count.
  * Negative family sizes or children counts.
* **Invalid credit statuses**: Status records containing invalid statuses.

### 2. How Each Problem Was Handled
* **Missing Occupations**: Imputed all null or `"nan"` strings with `"Unspecified"`.
* **Duplicates**: Removed duplicate `ID` rows from application data, keeping the last record.
* **Inconsistencies**: Stripped all leading/trailing whitespace from string columns and standardized text to uppercase.
* **Logic Overrides**:
  * Enforced `CNT_CHILDREN` >= 0.
  * Enforced `CNT_FAM_MEMBERS` >= 1.
  * Forced `CNT_FAM_MEMBERS` to be at least `CNT_CHILDREN + 1` (a parent + children).
  * Enforced non-negativity on `AMT_INCOME_TOTAL`.
  * Filtered credit dataset to keep only rows with standard valid status codes (`C, 0, 1, 2, 3, 4, 5, X`).

### 3. Modified vs. Unchanged Columns
* **Modified / Cleaned Columns**:
  * `OCCUPATION_TYPE`: Nulls filled with `"Unspecified"`.
  * `CNT_CHILDREN` & `CNT_FAM_MEMBERS`: Value limits validated and corrected.
  * `CODE_GENDER`, `FLAG_OWN_CAR`, `FLAG_OWN_REALTY`: Standardized to uppercase.
  * `AMT_INCOME_TOTAL`: Value limits validated.
  * `STATUS`: Standardized to uppercase and filtered.
* **Unchanged Columns**:
  * `ID`, `NAME_INCOME_TYPE`, `NAME_EDUCATION_TYPE`, `NAME_FAMILY_STATUS`, `NAME_HOUSING_TYPE`, `DAYS_BIRTH`, `DAYS_EMPLOYED`, `FLAG_MOBIL`, `FLAG_WORK_PHONE`, `FLAG_PHONE`, `FLAG_EMAIL`, `MONTHS_BALANCE`.

### 4. Assumptions & Rationale
* **Customer ID Uniqueness**: Each ID should correspond to a unique client profile. Duplicate applications are dropped to prevent target bleeding when predicting approval.
* **Preserving Missing Occupations**: Dropping rows with missing `OCCUPATION_TYPE` would lose 7.9% of the dataset. Imputing with `"Unspecified"` retains the data for training.
* **Family Size Consistency**: A family size cannot be smaller than the number of children + 1, assuming there is at least one adult caretaker.

---

## 9. Machine Learning Pipeline Redesign (Anti-Leakage Mitigation)

### 1. The Core Data Leakage Problem
In the previous implementation, the training features included repayment history aggregates such as `CREDIT_HISTORY_LENGTH`, `LATE_PAYMENTS_COUNT`, and `REPAYMENT_CONSISTENCY`. Since the target label `APPROVED` is also derived directly from this monthly history, the model had direct access to the label via these proxy columns.
* **Why it failed**: This caused the models to achieve a perfect 1.000 F1 score during validation. However, a **new applicant** has no monthly log history with the bank yet. Serving the model in production required hardcoding dummy constants (e.g. late payments = 0), rendering the demographic predictor features completely useless.

### 2. The Redesign Solution
To resolve this:
* **Target Creation Only**: The monthly logs in `credit_record.csv` are used **strictly and exclusively** to generate a one-time binary target flag `APPROVED` for historical profiles.
* **Feature Discarding**: Features like `LATE_PAYMENTS_COUNT`, `REPAYMENT_CONSISTENCY`, and `CREDIT_HISTORY_LENGTH` are **completely discarded** and are never fed into the ML models.
* **Demographic Inference**: The models are trained and evaluated using only the demographic and financial data provided by the applicant at sign-up.

### 3. Features Used in the Redesigned Pipeline
* **Continuous Features (Standard Scaled)**:
  * `LOG_INCOME` (Log transformed INR monthly income), `AGE` (Years), `AGE_RISK_SCORE` (piecewise numeric age risk mapping), `EMPLOYED_YEARS` (Experience Years), `INCOME_PER_MEMBER`, `CNT_CHILDREN`, `CNT_FAM_MEMBERS`
* **Categorical Features (One-Hot Encoded)**:
  * `CODE_GENDER`, `FLAG_OWN_CAR`, `FLAG_OWN_REALTY`, `NAME_INCOME_TYPE`, `NAME_EDUCATION_TYPE`, `NAME_FAMILY_STATUS`, `NAME_HOUSING_TYPE`, `OCCUPATION_TYPE`
* **Engineered & Binned Demographic Columns**:
  * `AGE_GROUP` (Binned: 18-25, 26-40, 41-60, 60+), `INCOME_GROUP`, `FAMILY_SIZE_CAT`

### 4. Selection Bias Correction
To prevent the model from blindly approving all applicants (an artifact of selection bias where the historical database only contains log details for clients who were already issued a credit card by the bank), we inject synthetic bias-correction records:
* **Young & Unemployed** (Zero/low income, no assets) -> `APPROVED = 0`
* **Low Income + High Dependents** -> `APPROVED = 0`
* **Elderly Pensioners with low income and no assets** -> `APPROVED = 0`
This allows the machine learning algorithms to map realistic credit risk boundaries during training.

---

## 10. Model Evaluation & Selection (Post-Redesign)

The training process evaluated 8 distinct models on the redesigned, leakage-free test dataset:

### Model Comparison Table (Sorted by F1-Score)
| Algorithm | Accuracy | Precision | Recall | F1-Score | ROC-AUC | CV-Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Random Forest (Champion)** | **0.7035** | **0.6000** | **0.9600** | **0.7385** | **0.7332** | **0.6993** |
| **Naive Bayes** | 0.6860 | 0.5814 | 1.0000 | 0.7353 | 0.7405 | 0.6905 |
| **Decision Tree** | 0.6977 | 0.5966 | 0.9467 | 0.7320 | 0.7284 | 0.7168 |
| **Gradient Boosting** | 0.6919 | 0.6000 | 0.8800 | 0.7135 | 0.7455 | 0.6832 |
| **SVM** | 0.6686 | 0.5776 | 0.8933 | 0.7016 | 0.7222 | 0.7037 |
| **XGBoost** | 0.6802 | 0.5926 | 0.8533 | 0.6995 | 0.7391 | 0.6920 |
| **Logistic Regression** | 0.6395 | 0.5657 | 0.7467 | 0.6437 | 0.7079 | 0.6964 |
| **KNN** | 0.6453 | 0.5875 | 0.6267 | 0.6065 | 0.7047 | 0.6365 |

### Champion Model Selection Rationale
* **Selected Model**: **Random Forest Classifier** (trained with `class_weight='balanced'`).
* **Why it was chosen**: The Random Forest model achieved the highest Accuracy (`0.7035`), an F1-Score of `0.7385`, and a balanced ROC-AUC (`0.7332`) while correctly mapping risk bounds (assigning 0% approval probability to high-risk young unemployed edge-profiles and high approval probability to stable employed profiles).

