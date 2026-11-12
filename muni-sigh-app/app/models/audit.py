# app/models/audit.py
from datetime import datetime
from app import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    payload = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs', lazy=True)

    # ── Diccionario de etiquetas legibles para acciones ──
    ACTION_LABELS = {
        'CONTRACT_CREATE': 'Contrato creado',
        'CONTRACT_UPDATE': 'Contrato modificado',
        'CONTRACT_STATUS_CHANGE': 'Cambio de estado',
        'CONTRACT_UPLOAD': 'Contrato cargado (externo)',
        'PROVIDER_CREATE': 'Prestador creado',
        'PROVIDER_AUTO_CREATE': 'Prestador creado automáticamente (OCR)',
        'DEPARTMENT_CREATE': 'Departamento creado',
        'DEPARTMENT_AUTO_CREATE': 'Departamento creado automáticamente (OCR)',
        'DECREE_TEMPLATE_CREATE': 'Plantilla de decreto creada',
        'DECREE_TEMPLATE_UPDATE': 'Plantilla de decreto modificada',
        'DECREE_TEMPLATE_DELETE': 'Plantilla de decreto eliminada',
        'CONTRACT_DECREE_UPDATE': 'Decretos/VISTOS del contrato actualizados',
    'DOCUMENT_SIGNED': 'Documento firmado (rúbrica ágil)',
    'CONTRACT_SIGNED': 'Contrato firmado (rúbrica ágil)',
    }

    @property
    def action_label(self):
        """Retorna una etiqueta legible para la acción registrada."""
        return self.ACTION_LABELS.get(self.action, self.action)

    @property
    def user_display(self):
        """Retorna el nombre completo del usuario o 'Sistema' si no hay usuario."""
        if self.user:
            return self.user.full_name
        return 'Sistema'

    @property
    def user_role_display(self):
        """Retorna el rol del usuario asociado o cadena vacía."""
        if self.user:
            return self.user.role
        return ''

    @classmethod
    def get_entity_trail(cls, entity_type, entity_id, limit=50):
        """
        Retorna el historial cronológico de acciones para una entidad específica.
        Ordenado del más reciente al más antiguo.
        """
        return cls.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_contract_trail(cls, contract_id, limit=50):
        """
        Retorna el historial cronológico de acciones de un contrato.
        Ordenado del más reciente al más antiguo.
        """
        return cls.query.filter_by(
            entity_type='contract',
            entity_id=contract_id
        ).order_by(cls.timestamp.desc()).limit(limit).all()

    def __repr__(self):
        return f"<AuditLog Action: {self.action} Entity: {self.entity_type} ID: {self.entity_id}>"