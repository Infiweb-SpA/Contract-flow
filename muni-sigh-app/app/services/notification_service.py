# app/services/notification_service.py
import os
import json
import logging
from flask import url_for, request, current_app

from app import db
from app.models.user import User
from app.models.permission import RolePermission, Permission
from app.services.email_service import send_email

# Catálogo de eventos de notificación (acción -> etiqueta, módulo)
NOTIFICATION_EVENTS = [
    ('CONTRACT_CREATE', 'Contrato creado', 'Contratos'),
    ('CONTRACT_UPDATE', 'Contrato modificado', 'Contratos'),
    ('CONTRACT_STATUS_CHANGE', 'Cambio de estado de contrato', 'Contratos'),
    ('CONTRACT_UPLOAD', 'Contrato cargado (externo)', 'Contratos'),
    ('CONTRACT_DECREE_UPDATE', 'Decretos/VISTOS actualizados', 'Contratos'),
    ('DOCUMENT_DOWNLOADED', 'Documento descargado (PDF)', 'Contratos'),
    ('DOCUMENT_PRINTED', 'Documento impreso', 'Contratos'),
    ('DOCUMENT_SIGNED', 'Documento firmado (rúbrica)', 'Contratos'),
    ('CONTRACT_SIGNED', 'Contrato firmado (rúbrica)', 'Contratos'),
    ('PROVIDER_CREATE', 'Prestador creado', 'Prestadores'),
    ('PROVIDER_AUTO_CREATE', 'Prestador creado automáticamente (OCR)', 'Prestadores'),
    ('DEPARTMENT_CREATE', 'Departamento creado', 'Departamentos'),
    ('DEPARTMENT_AUTO_CREATE', 'Departamento creado automáticamente (OCR)', 'Departamentos'),
    ('DECREE_TEMPLATE_CREATE', 'Plantilla de decreto creada', 'Decretos'),
    ('DECREE_TEMPLATE_UPDATE', 'Plantilla de decreto modificada', 'Decretos'),
    ('DECREE_TEMPLATE_DELETE', 'Plantilla de decreto eliminada', 'Decretos'),
    ('USER_CREATE', 'Usuario creado', 'Usuarios'),
    ('USER_UPDATE', 'Usuario modificado', 'Usuarios'),
    ('USER_TOGGLE', 'Usuario activado/desactivado', 'Usuarios'),
    ('USER_PASSWORD_CHANGE', 'Cambio de contraseña', 'Usuarios'),
    ('USER_EMAIL_CHANGE', 'Cambio de correo electrónico', 'Usuarios'),
    ('USER_NOTIFICATION_PREF', 'Preferencia de notificaciones', 'Usuarios'),
    ('ROLE_CREATE', 'Rol creado', 'Roles y Permisos'),
    ('ROLE_DELETE', 'Rol eliminado', 'Roles y Permisos'),
    ('ROLE_PERMISSIONS_UPDATE', 'Permisos de rol actualizados', 'Roles y Permisos'),
    ('PERMISSION_CREATE', 'Permiso creado', 'Roles y Permisos'),
]


def get_disabled_actions(user):
    try:
        if not user.disabled_notifications:
            return set()
        data = json.loads(user.disabled_notifications)
        if isinstance(data, list):
            return set(data)
    except Exception:
        pass
    return set()


def set_disabled_actions(user, disabled_set):
    user.disabled_notifications = json.dumps(sorted(disabled_set)) if disabled_set else None


def _users_subscribed():
    """Usuarios activos con receive_email_notifications=1 y permiso view_audit."""
    try:
        # IDs de roles que tienen el permiso view_audit
        perm = Permission.query.filter_by(name='view_audit').first()
        if not perm:
            return []
        role_names = {rp.role_name for rp in RolePermission.query.filter_by(permission_id=perm.id).all()}
        if not role_names:
            return []
        return User.query.filter(
            User.is_active == 1,
            User.receive_email_notifications == 1,
            User.role.in_(list(role_names)),
        ).all()
    except Exception as e:
        logging.getLogger(__name__).warning("Error obteniendo usuarios suscritos: %s", e)
        return []


def _base_url():
    try:
        return request.url_root.rstrip('/')
    except RuntimeError:
        return os.environ.get('APP_BASE_URL', '').rstrip('/')


def notify_audit_event(action, entity_type, entity_id, user_id=None, payload=None):
    """
    Envía un correo a los usuarios suscritos informando un evento de auditoría.
    No debe generar registros de auditoría adicionales.
    """
    import json

    users = _users_subscribed()
    if not users:
        return

    # Filtrar usuarios que desactivaron este evento específico
    filtered = []
    for u in users:
        disabled = get_disabled_actions(u)
        if action not in disabled:
            filtered.append(u)
    users = filtered
    if not users:
        return

    # Nombre del responsable
    responsible = 'Sistema'
    if user_id:
        u = User.query.get(user_id)
        if u:
            responsible = f"{u.full_name} ({u.role})"

    # Detalles del payload
    details = ''
    if payload:
        try:
            details = json.dumps(payload, ensure_ascii=False)
        except Exception:
            details = str(payload)

    # Enlace al expediente (si es contrato)
    link = ''
    if entity_type == 'contract' and entity_id:
        base = _base_url()
        if base:
            link = f"{base}/contracts/{entity_id}"

    subject = f"[Contract Flow] Evento: {action}"
    for u in users:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e3a8a;">Contract Flow — Notificación de auditoría</h2>
            <table style="width:100%; border-collapse: collapse; font-size: 13px;">
                <tr><td style="padding:6px; font-weight:bold;">Evento</td><td style="padding:6px;">{action}</td></tr>
                <tr><td style="padding:6px; font-weight:bold;">Entidad</td><td style="padding:6px;">{entity_type} #{entity_id}</td></tr>
                <tr><td style="padding:6px; font-weight:bold;">Responsable</td><td style="padding:6px;">{responsible}</td></tr>
                <tr><td style="padding:6px; font-weight:bold;">Detalles</td><td style="padding:6px;">{details}</td></tr>
            </table>
            {f'<p style="margin-top:12px;"><a href="{link}">Ver expediente</a></p>' if link else ''}
            <p style="color:#64748b; font-size:12px; margin-top:16px;">
                Recibes este correo porque tienes activadas las notificaciones de auditoría.
            </p>
        </div>
        """
        text = f"Evento: {action}\nEntidad: {entity_type} #{entity_id}\nResponsable: {responsible}\nDetalles: {details}\n{link}"
        try:
            send_email(u.email, subject, html=html, text=text)
        except Exception as e:
            logging.getLogger(__name__).warning("Error enviando notificación a %s: %s", u.email, e)