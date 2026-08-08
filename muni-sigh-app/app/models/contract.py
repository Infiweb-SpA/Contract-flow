# app/models/contract.py
from datetime import datetime
from app import db


class Contract(db.Model):
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_providers.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
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
    
    pdf_file_path = db.Column(db.String(255), nullable=True)
    ocr_processed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='BORRADOR')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship('ServiceProvider', back_populates='contracts', lazy=True)
    department = db.relationship('Department', backref=db.backref('department_contracts', lazy=True))
    functions = db.relationship('ContractFunction', backref='contract', cascade='all, delete-orphan', lazy=True,
                                order_by='ContractFunction.function_order')
    
    # ← RELACIÓN AGREGADA: pagos mensuales asociados a este contrato
    payments = db.relationship('MonthlyPayment', back_populates='contract', lazy=True, cascade='all, delete-orphan')

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
            'CARGADO_EXTERNO': 'Cargado Externo'
        }
        return labels.get(self.creation_type, self.creation_type)

    def __repr__(self):
        return f"<Contract {self.contract_number} - {self.status}>"


class ContractFunction(db.Model):
    __tablename__ = 'contract_functions'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    function_order = db.Column(db.Integer, nullable=False)
    function_description = db.Column(db.Text, nullable=False)
    is_mandatory_for_payment = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContractFunction {self.function_order}: {self.function_description[:30]}...>"