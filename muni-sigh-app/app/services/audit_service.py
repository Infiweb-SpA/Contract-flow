# app/services/audit_service.py
import json
from flask import session
from app import db
from app.models.audit import AuditLog

def log_action(action: str, entity_type: str, entity_id: int, payload: dict = None, user_id: int = None):
    """Registra una acción en la bitácora de auditoría."""
    if user_id is None:
        user_id = session.get('user_id')

    payload_json = json.dumps(payload, ensure_ascii=False) if payload else None

    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload_json
    )
    db.session.add(audit_entry)
    db.session.commit()