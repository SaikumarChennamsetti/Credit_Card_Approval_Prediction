from flask import Blueprint, jsonify, request, current_app, session
from backend.services import (
    validate_prediction_input,
    execute_prediction,
    save_prediction_record,
    retrieve_prediction_history,
    retrieve_prediction_by_id,
    delete_prediction_by_id
)
from backend.utils import print_status

api_bp = Blueprint('api', __name__)

@api_bp.route('/', methods=['GET'])
def get_info():
    return jsonify({
        "success": True,
        "message": "Welcome to the Credit Card Approval Prediction System API.",
        "data": {
            "app_name": "Credit Card Approval Prediction API",
            "version": "1.0.0",
            "status": "active",
            "environment": current_app.config.get('FLASK_ENV', 'development')
        }
    }), 200

@api_bp.route('/health', methods=['GET'])
def health_check():
    import sys
    print("SYS MODULES keys containing 'services':", [k for k in sys.modules.keys() if 'services' in k])
    for k in ['backend.services', 'services']:
        if k in sys.modules:
            print(f"Module {k} ID: {id(sys.modules[k])}, Model: {getattr(sys.modules[k], '_MODEL', None)}, Preprocessor: {getattr(sys.modules[k], '_PREPROCESSOR', None)}")
            
    from backend.services import _MODEL, _PREPROCESSOR
    model_loaded = (_MODEL is not None and _PREPROCESSOR is not None)
    
    return jsonify({
        "success": True,
        "message": "System status check completed.",
        "data": {
            "status": "healthy",
            "model_loaded": model_loaded,
            "api_version": "1.0.0"
        }
    }), 200

@api_bp.route('/signup', methods=['POST'])
def api_signup():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error_code": "INVALID_JSON",
            "message": "Request payload must be formatted as a valid JSON object."
        }), 400
        
    data = request.get_json()
    full_name = data.get('full_name', '').strip()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    mobile = data.get('mobile', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    
    if not full_name or not username or not email or not password or not confirm_password:
        return jsonify({
            "success": False,
            "error_code": "MISSING_FIELDS",
            "message": "All fields except mobile number are required."
        }), 400
        
    import re
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return jsonify({
            "success": False,
            "error_code": "INVALID_EMAIL",
            "message": "Please provide a valid email address."
        }), 400
        
    if password != confirm_password:
        return jsonify({
            "success": False,
            "error_code": "PASSWORD_MISMATCH",
            "message": "Passwords do not match."
        }), 400
        
    if len(password) < 6:
        return jsonify({
            "success": False,
            "error_code": "WEAK_PASSWORD",
            "message": "Password must be at least 6 characters long."
        }), 400
        
    from backend.auth_services import register_user
    success, message, user = register_user(full_name, username, email, mobile, password)
    if success:
        return jsonify({
            "success": True,
            "message": "Registration successful.",
            "data": {
                "user_id": user.user_id,
                "username": user.username
            }
        }), 201
    else:
        return jsonify({
            "success": False,
            "error_code": "REGISTRATION_ERROR",
            "message": message
        }), 400

@api_bp.route('/login', methods=['POST'])
def api_login():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error_code": "INVALID_JSON",
            "message": "Request payload must be formatted as a valid JSON object."
        }), 400
        
    data = request.get_json()
    username_or_email = data.get('username_or_email', '').strip()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)
    
    if not username_or_email or not password:
        return jsonify({
            "success": False,
            "error_code": "MISSING_FIELDS",
            "message": "Please enter both username/email and password."
        }), 400
        
    from backend.auth_services import authenticate_user
    success, message, user = authenticate_user(username_or_email, password)
    if success:
        session.clear()
        session['user_id'] = user.user_id
        session['username'] = user.username
        session['full_name'] = user.full_name
        if remember_me:
            session.permanent = True
            
        return jsonify({
            "success": True,
            "message": "Login successful.",
            "data": {
                "user_id": user.user_id,
                "username": user.username,
                "full_name": user.full_name
            }
        }), 200
    else:
        return jsonify({
            "success": False,
            "error_code": "AUTHENTICATION_FAILED",
            "message": message
        }), 401

@api_bp.route('/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    return jsonify({
        "success": True,
        "message": "Session terminated successfully."
    }), 200

@api_bp.route('/predict', methods=['POST'])
def predict_approval():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error_code": "INVALID_JSON",
            "message": "Request payload must be formatted as a valid JSON object."
        }), 400
        
    data = request.get_json()
    
    from backend.services import _MODEL, _PREPROCESSOR
    if _MODEL is None or _PREPROCESSOR is None:
        current_app.logger.error("Prediction failed: Production model assets (model or preprocessor) are not loaded in memory.")
        return jsonify({
            "success": False,
            "error_code": "MODEL_NOT_LOADED",
            "message": "The machine learning model could not be loaded. Please check the model files, configuration paths, and startup logs."
        }), 500

    errors = validate_prediction_input(data)
    if errors:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_FAILED",
            "message": "Input validation failed. Please check field formats and values.",
            "data": {
                "validation_details": errors
            }
        }), 422
        
    try:
        result = execute_prediction(data)
        
        user_id = session.get('user_id')
        record_id = save_prediction_record(data, result, user_id=user_id, model_version="1.0.0")
        result["record_id"] = record_id
        
        return jsonify({
            "success": True,
            "message": "Prediction executed and saved successfully.",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "PREDICTION_ERROR",
            "message": f"An error occurred while calculating the prediction: {str(e)}"
        }), 500


@api_bp.route('/history', methods=['GET'])
def get_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    filters = {}
    pred_res = request.args.get('prediction_result', None)
    if pred_res is not None:
        filters['prediction_result'] = int(pred_res)
        
    app_id = request.args.get('applicant_id', None)
    if app_id:
        filters['applicant_id'] = app_id
        
    risk = request.args.get('risk_level', None)
    if risk:
        filters['risk_level'] = risk

    user_id = session.get('user_id')
    try:
        records, total_count, total_pages = retrieve_prediction_history(
            user_id=user_id, page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order, filters=filters
        )
        return jsonify({
            "success": True,
            "message": "Prediction history retrieved successfully.",
            "data": {
                "records": records,
                "total_records": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "records_per_page": per_page
            }
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "HISTORY_QUERY_ERROR",
            "message": f"Failed to retrieve history logs: {str(e)}"
        }), 500

@api_bp.route('/history/<int:record_id>', methods=['GET'])
def get_prediction_detail(record_id):
    user_id = session.get('user_id')
    try:
        record = retrieve_prediction_by_id(record_id, user_id=user_id)
        if record:
            return jsonify({
                "success": True,
                "message": "Prediction record details retrieved successfully.",
                "data": record
            }), 200
        else:
            return jsonify({
                "success": False,
                "error_code": "RECORD_NOT_FOUND",
                "message": f"Prediction record with ID {record_id} not found."
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": f"Could not retrieve record detail: {str(e)}"
        }), 500

@api_bp.route('/history/<int:record_id>', methods=['DELETE'])
def delete_prediction_record(record_id):
    user_id = session.get('user_id')
    try:
        deleted = delete_prediction_by_id(record_id, user_id=user_id)
        if deleted:
            return jsonify({
                "success": True,
                "message": f"Prediction record ID {record_id} successfully deleted from history."
            }), 200
        else:
            return jsonify({
                "success": False,
                "error_code": "RECORD_NOT_FOUND",
                "message": f"Prediction record with ID {record_id} not found."
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error_code": "DELETE_ERROR",
            "message": f"Could not delete record: {str(e)}"
        }), 500


@api_bp.route('/contact', methods=['POST'])
def submit_contact_message():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error_code": "INVALID_JSON",
            "message": "Request payload must be formatted as a valid JSON object."
        }), 400

    data = request.get_json()
    full_name = data.get('full_name', '')
    email = data.get('email', '')
    subject = data.get('subject', '')
    message = data.get('message', '')

    user_id = session.get('user_id')

    from backend.services import save_contact_message
    try:
        saved_msg = save_contact_message(
            full_name=full_name,
            email=email,
            subject=subject,
            message=message,
            user_id=user_id
        )
        return jsonify({
            "success": True,
            "message": "Your message has been submitted successfully.",
            "data": saved_msg
        }), 201
    except ValueError as val_err:
        return jsonify({
            "success": False,
            "error_code": "VALIDATION_FAILED",
            "message": str(val_err)
        }), 400
    except Exception as db_err:
        return jsonify({
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": "A database error occurred. Please try again later."
        }), 500

