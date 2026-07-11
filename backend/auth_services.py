from werkzeug.security import generate_password_hash, check_password_hash
from backend.models import db, User
from datetime import datetime
from backend.utils import get_ist_time
import logging

def register_user(full_name: str, username: str, email: str, mobile: str, password: str) -> tuple:
    try:
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            return False, "Username is already taken.", None
            
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return False, "Email address is already registered.", None

        password_hash = generate_password_hash(password)
        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            mobile=mobile if mobile else None,
            password_hash=password_hash
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return True, "User registered successfully.", new_user
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to register user: {str(e)}", exc_info=True)
        return False, f"An error occurred during registration: {str(e)}", None

def authenticate_user(username_or_email: str, password: str) -> tuple:
    try:
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user:
            return False, "Invalid username/email or password.", None
            
        if check_password_hash(user.password_hash, password):
            user.last_login = get_ist_time()
            db.session.commit()
            return True, "Authentication successful.", user
            
        return False, "Invalid username/email or password.", None
    except Exception as e:
        logging.error(f"Failed to authenticate user: {str(e)}", exc_info=True)
        return False, f"An error occurred during authentication: {str(e)}", None

def get_user_by_id(user_id: str) -> User:
    try:
        return db.session.get(User, user_id)
    except Exception as e:
        logging.error(f"Failed to retrieve user: {str(e)}", exc_info=True)
        return None
