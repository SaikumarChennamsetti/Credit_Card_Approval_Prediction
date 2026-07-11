from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy
from backend.utils import get_ist_time, datetime_to_ist_iso

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    
    user_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=get_ist_time, nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User user_id={self.user_id} username={self.username}>"

class PredictionHistory(db.Model):
    __tablename__ = 'prediction_history'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=True)
    applicant_id = db.Column(db.String(50), nullable=True)
    prediction_result = db.Column(db.Integer, nullable=False)
    approval_probability = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    customer_input = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=get_ist_time, nullable=False)
    model_version = db.Column(db.String(50), default="1.0.0", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "applicant_id": self.applicant_id,
            "prediction_result": self.prediction_result,
            "approval_probability": self.approval_probability,
            "confidence_score": self.confidence_score,
            "explanation": self.explanation,
            "customer_input": self.customer_input,
            "created_at": datetime_to_ist_iso(self.created_at),
            "model_version": self.model_version
        }

    def __repr__(self) -> str:
        return f"<PredictionHistory id={self.id} result={self.prediction_result} prob={self.approval_probability:.4f}>"


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True), default=get_ist_time, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "subject": self.subject,
            "message": self.message,
            "submitted_at": datetime_to_ist_iso(self.submitted_at)
        }

    def __repr__(self) -> str:
        return f"<ContactMessage id={self.id} email={self.email} subject={self.subject}>"


