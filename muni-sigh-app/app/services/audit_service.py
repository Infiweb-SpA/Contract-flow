# app/services/audit_service.py
import json
from datetime import datetime
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


def get_contract_audit_trail(contract_id: int, limit: int = 50) -> list:
    """
    Retorna el historial de actividad formateado de un contrato y sus pagos.
    Cada elemento es un dict con: timestamp, action_label, user_name, user_role,
    details y entity_type.
    """
    raw_trail = AuditLog.get_contract_trail(contract_id, limit=limit)

    formatted = []
    for entry in raw_trail:
        # Extraer detalles del payload
        details = ''
        if entry.payload:
            try:
                payload_data = json.loads(entry.payload)
                details = _format_payload(entry.action, payload_data)
            except (json.JSONDecodeError, TypeError):
                details = str(entry.payload)

        formatted.append({
            'timestamp': entry.timestamp,
            'timestamp_display': entry.timestamp.strftime('%d/%m/%Y %H:%M'),
            'action': entry.action,
            'action_label': entry.action_label,
            'user_name': entry.user_display,
            'user_role': entry.user_role_display,
            'entity_type': entry.entity_type,
            'entity_id': entry.entity_id,
            'details': details,
        })

    return formatted


def _format_payload(action: str, payload: dict) -> str:
    """
    Genera una descripción legible a partir del payload de la acción.
    """
    parts = []

    if action == 'CONTRACT_CREATE':
        if payload.get('contract_number'):
            parts.append(f"Contrato N° {payload['contract_number']}")

    elif action == 'CONTRACT_UPDATE':
        if payload.get('contract_number'):
            parts.append(f"Contrato N° {payload['contract_number']}")

    elif action == 'CONTRACT_STATUS_CHANGE':
        from_label = _status_label(payload.get('from', ''))
        to_label = _status_label(payload.get('to', ''))
        parts.append(f"{from_label} → {to_label}")

    elif action == 'CONTRACT_UPLOAD':
        if payload.get('contract_number'):
            parts.append(f"Contrato N° {payload['contract_number']}")
        if payload.get('ocr'):
            parts.append("con extracción OCR")

    elif action == 'PAYMENT_CREATE':
        if payload.get('period'):
            parts.append(f"Período {payload['period']}")

    elif action in ('PAYMENT_RECHAZADO', 'PAYMENT_OBSERVADO'):
        if payload.get('reason'):
            parts.append(f"Motivo: {payload['reason']}")

    elif action in ('PAYMENT_VISADO_DEPTO', 'PAYMENT_APROBADO_RRHH', 'PAYMENT_APROBADO_FINANZAS'):
        pass  # La etiqueta de acción ya es suficiente

    elif action == 'PROVIDER_CREATE':
        if payload.get('rut'):
            parts.append(f"RUT: {payload['rut']}")

    elif action == 'PROVIDER_AUTO_CREATE':
        if payload.get('rut'):
            parts.append(f"RUT: {payload['rut']} (vía OCR)")

    elif action == 'DEPARTMENT_CREATE':
        if payload.get('code') and payload.get('name'):
            parts.append(f"{payload['code']} — {payload['name']}")

    elif action == 'DEPARTMENT_AUTO_CREATE':
        if payload.get('code') and payload.get('name'):
            parts.append(f"{payload['code']} — {payload['name']} (vía OCR)")

    return ' — '.join(parts) if parts else ''


def _status_label(status_code: str) -> str:
    """Convierte un código de estado a su etiqueta legible."""
    labels = {
        'BORRADOR': 'Borrador',
        'CREADO_PARA_FIRMA': 'Creado para Firma',
        'INGRESADO': 'Ingresado',
        'EN_EJECUCION': 'En Ejecución',
        'FINALIZADO': 'Finalizado',
        'PENDIENTE_REVISION': 'Pendiente de Revisión',
        'VISADO_JEFE_DEPTO': 'Visado por Jefe de Depto.',
        'APROBADO_RRHH': 'Aprobado por RRHH',
        'APROBADO_FINANZAS': 'Aprobado por Finanzas',
        'RECHAZADO': 'Rechazado',
        'OBSERVADO': 'Observado',
    }
    return labels.get(status_code, status_code)