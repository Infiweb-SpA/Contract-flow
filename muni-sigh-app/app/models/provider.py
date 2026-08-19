# app/models/provider.py
from datetime import datetime
from app import db

class ServiceProvider(db.Model):
    __tablename__ = 'service_providers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rut = db.Column(db.String(20), nullable=False, unique=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    paternal_last_name = db.Column(db.String(100), nullable=False)
    maternal_last_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)

    # ── Nuevos campos personales (Contrato Freire) ──
    profession_or_trade = db.Column(db.String(150), nullable=True)   # "Fonoaudiología"
    nationality = db.Column(db.String(50), nullable=True, default='Chilena')
    civil_status = db.Column(db.String(30), nullable=True)           # "Soltero/a", "Casado/a"
    birth_date = db.Column(db.Date, nullable=True)

    # ── Datos bancarios (info estática para depósito, NO para validación de pagos) ──
    bank_name = db.Column(db.String(100), nullable=True)
    account_type = db.Column(db.String(50), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relación sincronizada con back_populates hacia Contract
    contracts = db.relationship('Contract', back_populates='provider', lazy=True, cascade="all, delete-orphan")

    @property
    def full_name(self):
        maternal = f" {self.maternal_last_name}" if self.maternal_last_name else ""
        return f"{self.first_name} {self.paternal_last_name}{maternal}"

    def __repr__(self):
        return f"<ServiceProvider {self.rut} - {self.full_name}>"