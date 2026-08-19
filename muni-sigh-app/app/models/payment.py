# app/models/payment.py
from datetime import datetime
from app import db


class MonthlyPayment(db.Model):
    __tablename__ = 'monthly_payments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id', ondelete='CASCADE'), nullable=False)
    payment_year = db.Column(db.Integer, nullable=False)
    payment_month = db.Column(db.Integer, nullable=False)
    amount_to_pay = db.Column(db.Float, nullable=False)
    report_file_path = db.Column(db.String(255), nullable=True)
    
    approval_status = db.Column(db.String(30), nullable=False, default='PENDIENTE_REVISION')
    rejection_observations = db.Column(db.Text, nullable=True)
    
    reviewed_by_depto_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by_rrhh_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_by_finanzas_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('contract_id', 'payment_year', 'payment_month', name='uix_contract_period'),
    )

    # ← RELACIÓN AGREGADA: acceso al contrato desde el pago
    # ✅ LÍNEA NUEVA
    contract = db.relationship('Contract', backref=db.backref('payments', lazy=True, cascade='all, delete-orphan'), lazy=True)
    
    reviewed_by_depto = db.relationship('User', foreign_keys=[reviewed_by_depto_user_id])
    approved_by_rrhh = db.relationship('User', foreign_keys=[approved_by_rrhh_user_id])
    approved_by_finanzas = db.relationship('User', foreign_keys=[approved_by_finanzas_user_id])

    checklists = db.relationship('PaymentFunctionChecklist', backref='monthly_payment', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MonthlyPayment Contract: {self.contract_id} Period: {self.payment_month}/{self.payment_year} - Status: {self.approval_status}>"


class PaymentFunctionChecklist(db.Model):
    __tablename__ = 'payment_function_checklist'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    monthly_payment_id = db.Column(db.Integer, db.ForeignKey('monthly_payments.id', ondelete='CASCADE'), nullable=False)
    contract_function_id = db.Column(db.Integer, db.ForeignKey('contract_functions.id', ondelete='CASCADE'), nullable=False)
    
    status = db.Column(db.String(20), nullable=False, default='CUMPLIDO')
    comments = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<PaymentFunctionChecklist Payment ID: {self.monthly_payment_id} Function ID: {self.contract_function_id} - {self.status}>"