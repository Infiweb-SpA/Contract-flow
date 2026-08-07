# app/services/pdf_generator.py
from flask import render_template

def generate_contract_html(contract):
    """Renderiza la plantilla HTML oficial del contrato para impresión o vista previa."""
    return render_template('contracts/pdf_template.html', contract=contract)