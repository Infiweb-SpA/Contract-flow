# app/services/pdf_generator.py
from flask import render_template, make_response
from xhtml2pdf import pisa
import io


def generate_contract_html(contract):
    """
    Renderiza la plantilla HTML oficial del contrato para impresión o vista previa.
    El navegador puede imprimir directamente con Ctrl+P / window.print().
    """
    return render_template('contracts/pdf_template.html', contract=contract)


def generate_contract_pdf(contract):
    """
    Genera un PDF real a partir del HTML del contrato usando xhtml2pdf.
    Es 100% Python, no requiere instalar programas externos al sistema.
    
    Requiere instalar la librería:
        pip install xhtml2pdf
    """
    html_string = render_template('contracts/pdf_template.html', contract=contract)
    pdf_buffer = io.BytesIO()
    
    # Generar PDF en memoria
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
    
    if pisa_status.err:
        raise Exception(f"Error al generar PDF: {pisa_status.err}")
    
    pdf_buffer.seek(0)
    filename = f"Contrato_{contract.contract_number}.pdf"
    return pdf_buffer, filename


def make_pdf_response(contract):
    """
    Crea una respuesta Flask lista para descargar el PDF.
    Se usa en la ruta /contracts/<id>/download-pdf
    """
    pdf_buffer, filename = generate_contract_pdf(contract)
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response