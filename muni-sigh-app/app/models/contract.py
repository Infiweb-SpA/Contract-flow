# app/models/contract.py
from datetime import datetime
from app import db


class Contract(db.Model):
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_providers.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    # ── Trazabilidad: quién creó y modificó ──
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    last_modified_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    creation_type = db.Column(db.String(50), default='CREADO')
    contract_number = db.Column(db.String(50), unique=True, nullable=False)
    decline_number = db.Column(db.String(50), nullable=True)
    decline_date = db.Column(db.Date, nullable=True)
    position_title = db.Column(db.String(150), nullable=False)
    program_name = db.Column(db.String(150), nullable=True)
    monthly_amount_gross = db.Column(db.Float, nullable=False)
    total_contract_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # ── Nuevos campos (estructura Freire) ──
    contract_date = db.Column(db.Date, nullable=True)
    budget_account = db.Column(db.String(50), nullable=True)
    sub_program = db.Column(db.String(30), nullable=True)
    cost_center = db.Column(db.String(30), nullable=True)
    payment_modality = db.Column(db.String(30), nullable=True, default='MENSUAL_FIJO')

    # ── Datos del Decreto Alcaldicio (estructura Cunco, página 2) ──
    provider_address = db.Column(db.String(255), nullable=True)      # Domicilio del prestador
    provider_comuna = db.Column(db.String(100), nullable=True)       # Comuna de domicilio
    hours_weekly = db.Column(db.Integer, nullable=True, default=44)  # Jornada horas semanales
    total_amount_words = db.Column(db.String(255), nullable=True)    # Monto total en palabras
    # ── Firmas del Decreto Alcaldicio (dibujo canvas, dataURL PNG) ──
    mayor_signature = db.Column(db.Text, nullable=True)              # Firma del Alcalde
    secretary_signature = db.Column(db.Text, nullable=True)          # Firma del Secretario Municipal

    pdf_file_path = db.Column(db.String(255), nullable=True)
    ocr_processed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='BORRADOR')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship('ServiceProvider', back_populates='contracts', lazy=True)
    department = db.relationship('Department', backref=db.backref('department_contracts', lazy=True))

    # ── Relaciones de trazabilidad ──
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id], lazy=True)
    last_modified_by_user = db.relationship('User', foreign_keys=[last_modified_by_user_id], lazy=True)

    functions = db.relationship('ContractFunction', backref='contract', cascade='all, delete-orphan', lazy=True,
                                order_by='ContractFunction.function_order')

    # ── Decretos y Antecedentes Previos (VISTOS) ──
    decrees = db.relationship('ContractDecree', backref='contract', cascade='all, delete-orphan', lazy=True,
                              order_by='ContractDecree.display_order')

    # ── Firmas ágiles (rúbrica) con metadatos de validación ──
    signatures = db.relationship('ContractSignature', backref='contract', cascade='all, delete-orphan', lazy=True,
                                 order_by='ContractSignature.signed_at')

    @property
    def status_label(self):
        labels = {
            'BORRADOR': 'Borrador',
            'CREADO_PARA_FIRMA': 'Creado para Firma',
            'INGRESADO': 'Ingresado',
            'EN_EJECUCION': 'En Ejecución',
            'FINALIZADO': 'Finalizado'
        }
        return labels.get(self.status, self.status)

    @property
    def creation_type_label(self):
        labels = {
            'CREADO': 'Creado',
            'CARGADO_EXTERNO': 'Cargado Externo',
            'PROCESADO_OCR': 'Procesado OCR'
        }
        return labels.get(self.creation_type, self.creation_type)

    @property
    def payment_modality_label(self):
        labels = {
            'MENSUAL_FIJO': 'Mensual Fijo',
            'POR_PRODUCTO': 'Por Producto'
        }
        return labels.get(self.payment_modality, self.payment_modality or 'No definida')

    @property
    def duration_months(self):
        if self.start_date and self.end_date:
            return (self.end_date.year - self.start_date.year) * 12 + (self.end_date.month - self.start_date.month) + 1
        return 0

    @property
    def budget_code_full(self):
        parts = []
        if self.budget_account:
            parts.append(self.budget_account)
        if self.sub_program:
            parts.append(self.sub_program)
        if self.cost_center:
            parts.append(f"Centro de Costo {self.cost_center}")
        return ' '.join(parts) if parts else None

    def __repr__(self):
        return f"<Contract {self.contract_number} - {self.status}>"


class ContractFunction(db.Model):
    __tablename__ = 'contract_functions'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    function_order = db.Column(db.Integer, nullable=False)
    function_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContractFunction {self.function_order}: {self.function_description[:30]}...>"


class ContractSignature(db.Model):
    """Firma ágil (rúbrica) con metadatos inmutables de validación."""
    __tablename__ = 'contract_signatures'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False)

    # Firmante (sesión activa)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    signer_rut = db.Column(db.String(20), nullable=False)
    signer_name = db.Column(db.String(200), nullable=False)
    signer_role = db.Column(db.String(50), nullable=True)

    # Metadatos inmutables
    signed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(64), nullable=True)
    ip = db.Column(db.String(64), nullable=True)  # alias
    user_agent = db.Column(db.Text, nullable=True)
    device_type = db.Column(db.String(50), nullable=True)
    device_info = db.Column(db.Text, nullable=True)
    document_hash = db.Column(db.String(64), nullable=False)
    document_hash_sha256 = db.Column(db.String(64), nullable=True)  # alias

    # Firma vectorial + validación
    signature_image = db.Column(db.Text, nullable=True)
    signature_data = db.Column(db.Text, nullable=True)  # alias
    validation_code = db.Column(db.String(64), nullable=False, unique=True)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='contract_signatures', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'user_id': self.user_id,
            'signer_rut': self.signer_rut,
            'signer_name': self.signer_name,
            'signer_role': self.signer_role,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'timestamp': self.signed_at.isoformat() if self.signed_at else None,
            'ip_address': self.ip_address or self.ip,
            'ip': self.ip_address or self.ip,
            'user_agent': self.user_agent,
            'device_type': self.device_type,
            'document_hash': self.document_hash or self.document_hash_sha256,
            'document_hash_sha256': self.document_hash or self.document_hash_sha256,
            'sha256': self.document_hash or self.document_hash_sha256,
            'signature_image': self.signature_image or self.signature_data,
            'signature': self.signature_image or self.signature_data,
            'validation_code': self.validation_code,
            'is_valid': bool(self.is_valid),
        }

    def __repr__(self):
        return f"<ContractSignature {self.validation_code} by {self.signer_name}>"