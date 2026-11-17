# app/models/verification_code.py
from datetime import datetime, timedelta
from app import db
import uuid


class VerificationCode(db.Model):
    """Código de un solo uso (OTP) con expiración para validación de identidad."""
    __tablename__ = 'verification_codes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_uuid = db.Column(db.String(36), nullable=False, unique=True, index=True)

    email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)

    purpose = db.Column(db.String(50), nullable=False)          # CONTRACT_SIGN_USER, etc.
    entity_type = db.Column(db.String(50), nullable=True)       # contract, decree_template, user
    entity_id = db.Column(db.Integer, nullable=True)
    signer_kind = db.Column(db.String(30), nullable=True)       # USER, ALCALDE, PROVIDER, ...

    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=5)
    is_valid = db.Column(db.Boolean, nullable=False, default=True)

    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_user_id], lazy=True)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def can_attempt(self):
        return self.is_valid and not self.is_expired and self.attempts < self.max_attempts and self.used_at is None

    def __repr__(self):
        return f"<VerificationCode {self.request_uuid} {self.purpose} {self.email}>"