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