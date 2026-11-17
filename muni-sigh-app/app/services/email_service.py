# app/services/email_service.py
import os
import logging
import requests
from flask import current_app


RESEND_API_URL = "https://api.resend.com/emails"


def _config(key, default=None):
    try:
        return current_app.config.get(key, os.environ.get(key, default))
    except RuntimeError:
        return os.environ.get(key, default)


def send_email(to, subject, html=None, text=None, from_email=None, from_name=None):
    """
    Envía un correo usando Resend. Devuelve True si fue aceptado.
    En desarrollo (sin RESEND_API_KEY) registra el correo en el log y devuelve True
    para no bloquear el flujo.
    """
    api_key = _config('RESEND_API_KEY')
    if not api_key:
        logging.getLogger(__name__).warning(
            "RESEND_API_KEY no configurado. Correo NO enviado a %s | Asunto: %s", to, subject
        )
        return True

    from_addr = from_email or _config('RESEND_FROM_EMAIL', 'no-reply@municipalidaddecunco.cl')
    name = from_name or _config('RESEND_FROM_NAME', 'Contract Flow')
    sender = f"{name} <{from_addr}>"

    # Modo prueba: redirigir todos los correos a un destinatario autorizado por Resend
    test_to = _config('RESEND_TEST_TO')
    original_to = to
    if test_to:
        to = test_to
        logging.getLogger(__name__).info(
            "RESEND_TEST_TO activo: correo redirigido de %s a %s", original_to, test_to
        )

    payload = {
        "from": sender,
        "to": [to] if isinstance(to, str) else list(to),
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text
    if not html and not text:
        payload["text"] = subject

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=20)
        if resp.status_code in (200, 201):
            return True
        logging.getLogger(__name__).error(
            "Resend error %s: %s", resp.status_code, resp.text
        )
        return False
    except Exception as e:
        logging.getLogger(__name__).error("Error enviando correo con Resend: %s", e)
        return False


def send_otp_email(to, code, purpose_label="verificación", expires_minutes=10):
    subject = f"Código de {purpose_label} - Contract Flow"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color: #1e3a8a;">Contract Flow</h2>
        <p>Su código de {purpose_label} es:</p>
        <div style="font-size: 28px; font-weight: bold; letter-spacing: 6px;
                    background: #f1f5f9; padding: 12px 16px; border-radius: 8px;
                    text-align: center; margin: 16px 0;">
            {code}
        </div>
        <p>Este código es de <strong>un solo uso</strong> y expira en
           <strong>{expires_minutes} minutos</strong>.</p>
        <p style="color: #64748b; font-size: 12px;">
            Si usted no solicitó este código, ignore este mensaje.
        </p>
    </div>
    """
    text = f"Su código de {purpose_label} es: {code}. Expira en {expires_minutes} minutos."
    return send_email(to, subject, html=html, text=text)