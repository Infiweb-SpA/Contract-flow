# app/models/decree.py
from datetime import datetime
from app import db


# ── Catálogo de tipos de decreto (uso compartido) ──
DECREE_TYPE_LABELS = {
    'PRESUPUESTO_ANUAL': 'Presupuesto Anual / Desgloses',
    'PROGRAMA_MUNICIPAL': 'Programa Municipal / POA',
    'CONTRATO_ANTERIOR': 'Contrato Anterior del Prestador',
    'CONTRATO_ACTUAL': 'Contrato Actual',
    'FICHA_RRHH': 'Ficha de Ingreso (RRHH)',
    'SUBROGANCIA_ALCALDE': 'Subrogancia de Alcalde',
    'SUBROGANCIA_CONTROL': 'Subrogancia Dirección de Control',
    'BASE_LEGAL': 'Base Legal (CGR / Leyes)',
    'ANTECEDENTE_INSTITUCIONAL': 'Antecedente Institucional',
    'OTRO': 'Otro Antecedente',
}


def _decree_type_label(decree_type):
    """Helper para etiquetar un tipo de decreto desde templates y modelos."""
    return DECREE_TYPE_LABELS.get(decree_type, decree_type)


class DecreeTemplate(db.Model):
    """
    Catálogo maestro de decretos/antecedentes estandarizados (VISTOS).
    Son las plantillas fijas del año (presupuesto, desgloses, subrogancias,
    bases legales) que se precargan automáticamente en todo borrador nuevo.
    """
    __tablename__ = 'decree_templates'

    id = db.Column(db.Integer, primary_key=True)
    decree_type = db.Column(db.String(50), nullable=False, default='OTRO')
    decree_number = db.Column(db.String(100), nullable=True)
    decree_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def decree_type_label(self):
        return _decree_type_label(self.decree_type)

    def __repr__(self):
        return f"<DecreeTemplate {self.id}: {self.decree_type} {self.decree_number}>"


class ContractDecree(db.Model):
    """
    Instancia de un decreto/antecedente (VISTO) asociado a un contrato.
    Si proviene del catálogo se copia como snapshot (origin PLANTILLA),
    de modo que editar la plantilla no altere contratos ya creados.
    """
    __tablename__ = 'contract_decrees'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)

    # Referencia a la plantilla de origen (opcional, para trazabilidad)
    template_id = db.Column(db.Integer, db.ForeignKey('decree_templates.id', ondelete='SET NULL'), nullable=True)

    decree_type = db.Column(db.String(50), nullable=False, default='OTRO')
    decree_number = db.Column(db.String(100), nullable=True)
    decree_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=False)

    # PLANTILLA: copiado desde el catálogo maestro | MANUAL: ingresado a mano
    origin = db.Column(db.String(20), default='PLANTILLA', nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    template = db.relationship('DecreeTemplate', lazy=True)

    @property
    def decree_type_label(self):
        return _decree_type_label(self.decree_type)

    @property
    def origin_label(self):
        return 'Plantilla' if self.origin == 'PLANTILLA' else 'Manual'

    def __repr__(self):
        return f"<ContractDecree contract={self.contract_id} order={self.display_order}>"


# =============================================================================
# AGRUPACIÓN VISTOS / DECRETO (estructura Cunco)
# =============================================================================
# Orden canónico de los tipos admitidos en el bloque VISTOS (página 1).
# El bloque final DECRETO (página 2) se estructura aparte con puntos 1-3.
VISTOS_TYPE_ORDER = [
    'PRESUPUESTO_ANUAL',
    'PROGRAMA_MUNICIPAL',
    'CONTRATO_ANTERIOR',
    'FICHA_RRHH',
    'SUBROGANCIA_ALCALDE',
    'SUBROGANCIA_CONTROL',
    'ANTECEDENTE_INSTITUCIONAL',
    'OTRO',  # antecedentes no clasificados del prestador (al final)
]

# Tipos que NUNCA aparecen como VISTOS seleccionables:
#  - BASE_LEGAL: se inyecta fijado en la plantilla (Resolución CGR / Oficio CGR / Ley 18.695).
#  - CONTRATO_ACTUAL: es el objeto del propio punto 1 del DECRETO (página 2).
VISTOS_EXCLUDED_TYPES = ('BASE_LEGAL', 'CONTRATO_ACTUAL')

# Tipos visibles en el paso 4 del stepper (catálogo seleccionable).
VISTOS_SELECTABLE_TYPES = tuple(t for t in VISTOS_TYPE_ORDER)


def get_decree_type(obj):
    """ Lee decree_type de objeto o dict."""
    if isinstance(obj, dict):
        return obj.get('decree_type') or 'OTRO'
    return getattr(obj, 'decree_type', None) or 'OTRO'


def order_vistos(decrees):
    """
    Filtra y ordena los decretos para el bloque VISTOS:
    - Excluye BASE_LEGAL y CONTRATO_ACTUAL (se inyectan fijados en la plantilla).
    - Ordena según el orden canónico VISTOS_TYPE_ORDER, respetando display_order.
    Acepta objetos ContractDecree o dicts.
    """
    buckets = {t: [] for t in VISTOS_TYPE_ORDER}
    for d in decrees:
        t = get_decree_type(d)
        if t in VISTOS_EXCLUDED_TYPES:
            continue
        if t not in buckets:
            t = 'OTRO'
        buckets[t].append(d)

    ordered = []
    for t in VISTOS_TYPE_ORDER:
        ordered.extend(buckets[t])
    return ordered
