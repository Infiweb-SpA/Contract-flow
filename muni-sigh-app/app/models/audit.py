# app/models/audit.py
from datetime import datetime
from app import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # Ej: CONTRACT_CREATE, CONTRACT_UPLOAD, OCR_EDIT
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    payload = db.Column(db.Text, nullable=True)           # JSON o texto de cambios
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs', lazy=True)

    def __repr__(self):
        return f"<AuditLog Action: {self.action} Entity: {self.entity_type} ID: {self.entity_id}>"