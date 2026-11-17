# app/services/otp_service.py
import secrets
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, request

from app import db
from app.models.verification_code import VerificationCode
from app.services.email_service import send_otp_email


def _expiry_minutes():
    try:
        return int(current_app.config.get('OTP_EXPIRY_MINUTES', 10))
    except Exception:
        return 10


def _max_attempts():
    try:
        return int(current_app.config.get('OTP_MAX_ATTEMPTS', 5))
    except Exception:
        return 5


def _otp_length():
    try:
        return int(current_app.config.get('OTP_LENGTH', 6))
    except Exception:
        return 6


def generate_code():
    length = _otp_length()
    # Evitar códigos con ceros a la izquierda: generar número de `length` dígitos
    upper = 10 ** length
    lower = 10 ** (length - 1)
    return str(secrets.randbelow(upper - lower) + lower)


def request_otp(email, purpose, entity_type=None, entity_id=None,
                signer_kind=None, created_by_user_id=None,
                purpose_label="verificación"):
    """
    Genera un OTP, invalida los anteriores activos para el mismo propósito/entidad/email,
    lo persiste hasheado y lo envía por correo. Devuelve (request_uuid, code_plain) o (None, None).
    """
    email = (email or '').strip().lower()
    if not email:
        return None, None

    # Invalidar códigos activos previos
    prev = VerificationCode.query.filter_by(
        email=email, purpose=purpose, entity_type=entity_type, entity_id=entity_id, is_valid=True
    ).all()
    for c in prev:
        c.is_valid = False
    db.session.flush()

    code = generate_code()
    code_hash = generate_password_hash(code)
    request_uuid = uuid.uuid4().hex

    ip = None
    ua = None
    try:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        ua = request.headers.get('User-Agent', '')
    except RuntimeError:
        pass

    vc = VerificationCode(
        request_uuid=request_uuid,
        email=email,
        code_hash=code_hash,
        purpose=purpose,
        entity_type=entity_type,
        entity_id=entity_id,
        signer_kind=signer_kind,
        created_by_user_id=created_by_user_id,
        expires_at=datetime.utcnow() + timedelta(minutes=_expiry_minutes()),
        max_attempts=_max_attempts(),
        ip_address=ip,
        user_agent=ua,
        is_valid=True,
    )
    db.session.add(vc)
    db.session.commit()

    send_otp_email(to=email, code=code, purpose_label=purpose_label,
                   expires_minutes=_expiry_minutes())

    return request_uuid, code


def verify_otp(request_uuid, code):
    """
    Verifica un OTP. Devuelve (ok: bool, verification_code or None, error_msg).
    Marca el código como usado si es válido.
    """
    if not request_uuid or not code:
        return False, None, "Código o identificador faltante."

    vc = VerificationCode.query.filter_by(request_uuid=request_uuid).first()
    if not vc:
        return False, None, "Código no encontrado."
    if not vc.is_valid:
        return False, None, "Código ya usado o invalidado."
    if vc.is_expired:
        vc.is_valid = False
        db.session.commit()
        return False, vc, "El código ha expirado."
    if vc.used_at is not None:
        return False, vc, "El código ya fue utilizado."
    if vc.attempts >= vc.max_attempts:
        vc.is_valid = False
        db.session.commit()
        return False, vc, "Se superó el número máximo de intentos."

    vc.attempts += 1
    db.session.flush()

    if not check_password_hash(vc.code_hash, str(code).strip()):
        db.session.commit()
        return False, vc, "Código incorrecto."

    vc.used_at = datetime.utcnow()
    vc.is_valid = False
    db.session.commit()
    return True, vc, None


def get_active_code(request_uuid):
    return VerificationCode.query.filter_by(request_uuid=request_uuid).first()