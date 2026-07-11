# REST API Documentation

This document describes the REST API endpoints provided by the Flask backend server of the Credit Card Approval Prediction System.

---

## Base URL
When running locally, the API server is available at:
`http://127.0.0.1:5000/api`

All JSON responses follow a standard format wrapper:
```json
{
    "success": true,
    "message": "...",
    "data": { ... }
}
```

Error responses follow a standard error format wrapper:
```json
{
    "success": false,
    "error_code": "...",
    "message": "..."
}
```

---

## Endpoints List

### 1. Welcome Info
* **Endpoint**: `/`
* **Method**: `GET`
* **Description**: Returns basic project information.
* **Response Code**: `200 OK`
* **Response Example**:
```json
{
    "success": true,
    "message": "Welcome to the Credit Card Approval Prediction System API.",
    "data": {
        "app_name": "Credit Card Approval Prediction API",
        "version": "1.0.0",
        "status": "active",
        "environment": "development"
    }
}
```

---

### 2. Server & Model Health Status Check
* **Endpoint**: `/health`
* **Method**: `GET`
* **Description**: Returns the loading status of the server and machine learning model assets.
* **Response Code**: `200 OK`
* **Response Example**:
```json
{
    "success": true,
    "message": "System status check completed.",
    "data": {
        "status": "healthy",
        "model_loaded": true,
        "api_version": "1.0.0"
    }
}
```

---

### 3. Credit Approval Inference Prediction
* **Endpoint**: `/predict`
* **Method**: `POST`
* **Description**: Accepts the applicant's demographic and financial parameters, executes preprocessing scaling and encoding, runs ML inference predictions, automatically saves the prediction log to the database history, and returns the saved record ID.
* **Request Header**: `Content-Type: application/json`

#### Request Parameters Details
* **Optional Fields**:
  * `applicant_id` (str): Unique custom string code representing applicant profile (e.g. `C-90281`).
* **Required Fields**:
  * `CODE_GENDER` (str): Gender identifier. Allowed values: `M` or `F`.
  * `FLAG_OWN_CAR` (str): Car ownership flag. Allowed values: `Y` or `N`.
  * `FLAG_OWN_REALTY` (str): Real estate ownership flag. Allowed values: `Y` or `N`.
  * `CNT_CHILDREN` (int): Number of children. Validation: must be `>= 0`.
  * `AMT_INCOME_TOTAL` (float): Total annual income. Validation: must be `> 0`.
  * `NAME_INCOME_TYPE` (str): Income source category. Example values: `Working`, `Commercial associate`, `State servant`, `Pensioner`, `Student`.
  * `NAME_EDUCATION_TYPE` (str): Education level category. Example values: `Higher education`, `Secondary / secondary special`, `Incomplete higher`, `Lower secondary`, `Academic degree`.
  * `NAME_FAMILY_STATUS` (str): Marital status category. Example values: `Married`, `Single / not married`, `Civil marriage`, `Separated`, `Widow`.
  * `NAME_HOUSING_TYPE` (str): Housing category. Example values: `House / apartment`, `With parents`, `Rented apartment`, `Municipal apartment`, `Office apartment`, `Co-op apartment`.
  * `AGE` (float): Age in years. Validation: must be between `18` and `120`.
  * `EMPLOYED_YEARS` (float): Duration of continuous job employment in years. Validation: must be `>= 0`.
  * `OCCUPATION_TYPE` (str): Job occupation category. Example values: `Managers`, `Laborers`, `Core staff`, `Sales staff`, `Accountants`, `Drivers`, etc.
  * `CNT_FAM_MEMBERS` (int): Family size count. Validation: must be `>= 1` and must be greater than `CNT_CHILDREN`.

* **Request Body Example**:
```json
{
    "applicant_id": "C-10928",
    "CODE_GENDER": "M",
    "FLAG_OWN_CAR": "Y",
    "FLAG_OWN_REALTY": "Y",
    "CNT_CHILDREN": 0,
    "AMT_INCOME_TOTAL": 180000,
    "NAME_INCOME_TYPE": "Working",
    "NAME_EDUCATION_TYPE": "Higher education",
    "NAME_FAMILY_STATUS": "Married",
    "NAME_HOUSING_TYPE": "House / apartment",
    "AGE": 35.5,
    "EMPLOYED_YEARS": 4.5,
    "OCCUPATION_TYPE": "Managers",
    "CNT_FAM_MEMBERS": 2
}
```
* **Success Response Code**: `200 OK`
* **Success Response Example**:
```json
{
    "success": true,
    "message": "Prediction executed and saved successfully.",
    "data": {
        "approved": true,
        "probability": 1.0,
        "confidence_score": 1.0,
        "risk_level": "Low",
        "explanation": "Your application exhibits strong income stability and a low risk profile.",
        "suggestions": [
            "Maintain your steady income stream and continue paying off existing debts on time."
        ],
        "record_id": 1
    }
}
```
* **Error Response Codes**:
  * `400 Bad Request`: Payload is not a valid JSON.
  * `422 Unprocessable Entity`: Input parameters failed validation criteria.
  * `500 Internal Server Error`: Inference processing failure.
* **Validation Error Example (`422 Unprocessable Entity`)**:
```json
{
    "success": false,
    "error_code": "VALIDATION_FAILED",
    "message": "Input validation failed. Please check field formats and values.",
    "data": {
        "validation_details": [
            "Missing required field: 'AMT_INCOME_TOTAL'",
            "AGE must be between 18 and 120",
            "Family size must be greater than number of children."
        ]
    }
}
```

---

### 4. Retrieve Prediction History Logs
* **Endpoint**: `/history`
* **Method**: `GET`
* **Description**: Retrieves a paginated list of past prediction records, with support for filtering and sorting parameters.
* **Query Parameters**:
  * `page` (int): Page number (default: `1`).
  * `per_page` (int): Number of records per page (default: `10`, max: `100`).
  * `sort_by` (str): Field to sort by (options: `created_at`, `approval_probability`, `prediction_result`; default: `created_at`).
  * `sort_order` (str): Sort direction (options: `asc`, `desc`; default: `desc`).
  * `prediction_result` (int): Filter by prediction result (options: `1` for Approved, `0` for Rejected).
  * `applicant_id` (str): Filter by unique applicant ID.
  * `risk_level` (str): Filter by risk level (options: `Low`, `Medium`, `High`).
* **Response Code**: `200 OK`
* **Response Example**:
```json
{
    "success": true,
    "message": "Prediction history retrieved successfully.",
    "data": {
        "records": [
            {
                "id": 1,
                "applicant_id": null,
                "prediction_result": 1,
                "approval_probability": 1.0,
                "confidence_score": 1.0,
                "explanation": "Your application exhibits strong income stability and a low risk profile.",
                "customer_input": {
                    "CODE_GENDER": "M",
                    "FLAG_OWN_CAR": "Y",
                    "FLAG_OWN_REALTY": "Y",
                    "CNT_CHILDREN": 0,
                    "AMT_INCOME_TOTAL": 180000,
                    "NAME_INCOME_TYPE": "Working",
                    "NAME_EDUCATION_TYPE": "Higher education",
                    "NAME_FAMILY_STATUS": "Married",
                    "NAME_HOUSING_TYPE": "House / apartment",
                    "AGE": 35.5,
                    "EMPLOYED_YEARS": 4.5,
                    "OCCUPATION_TYPE": "Managers",
                    "CNT_FAM_MEMBERS": 2
                },
                "created_at": "2026-07-06T13:58:20Z",
                "model_version": "1.0.0"
            }
        ],
        "total_records": 1,
        "total_pages": 1,
        "current_page": 1,
        "records_per_page": 10
    }
}
```

---

### 5. Retrieve Single Prediction Record details
* **Endpoint**: `/history/<int:record_id>`
* **Method**: `GET`
* **Description**: Retrieves full data parameters of a single prediction log from history matching `record_id`.
* **Response Code**: `200 OK` (if found), `404 Not Found` (if missing).
* **Response Example (`200 OK`)**:
```json
{
    "success": true,
    "message": "Prediction record details retrieved successfully.",
    "data": {
        "id": 1,
        "applicant_id": null,
        "prediction_result": 1,
        "approval_probability": 1.0,
        "confidence_score": 1.0,
        "explanation": "Your application exhibits strong income stability and a low risk profile.",
        "customer_input": {
            "CODE_GENDER": "M",
            "FLAG_OWN_CAR": "Y",
            "FLAG_OWN_REALTY": "Y",
            "CNT_CHILDREN": 0,
            "AMT_INCOME_TOTAL": 180000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
            "AGE": 35.5,
            "EMPLOYED_YEARS": 4.5,
            "OCCUPATION_TYPE": "Managers",
            "CNT_FAM_MEMBERS": 2
        },
        "created_at": "2026-07-06T13:58:20Z",
        "model_version": "1.0.0"
    }
}
```

---

### 6. Delete Single Prediction Record
* **Endpoint**: `/history/<int:record_id>`
* **Method**: `DELETE`
* **Description**: Removes a prediction log from the database table matching `record_id`.
* **Response Code**: `200 OK` (if deleted), `404 Not Found` (if missing).
* **Response Example (`200 OK`)**:
```json
{
    "success": true,
    "message": "Prediction record ID 1 successfully deleted from history."
}
```
