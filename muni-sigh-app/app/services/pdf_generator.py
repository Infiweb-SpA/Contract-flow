# app/services/pdf_generator.py
from flask import render_template, make_response, current_app
from xhtml2pdf import pisa
import io


def _build_preview_context(contract):
    """
    Construye un dict con todos los datos necesarios para el template,
    combinando datos del modelo Contract con datos institucionales de config.py.
    Funciona tanto con objetos SQLAlchemy como con dicts.
    """
    # ── Helper para leer atributos de objeto O dict ──
    def _get(obj, attr, default=''):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default) or default

    # ── Datos del prestador ──
    provider = _get(contract, 'provider', None)
    provider_name = ''
    provider_rut = ''
    provider_profession = ''
    provider_nationality = ''
    provider_civil_status = ''
    provider_address = ''
    provider_email = ''
    provider_bank_name = ''
    provider_account_type = ''
    provider_account_number = ''

    if provider:
        provider_name = _get(provider, 'full_name', '')
        provider_rut = _get(provider, 'rut', '')
        provider_profession = _get(provider, 'profession_or_trade', '')
        provider_nationality = _get(provider, 'nationality', '')
        provider_civil_status = _get(provider, 'civil_status', '')
        provider_address = _get(provider, 'address', '')
        provider_email = _get(provider, 'email', '')
        provider_bank_name = _get(provider, 'bank_name', '')
        provider_account_type = _get(provider, 'account_type', '')
        provider_account_number = _get(provider, 'account_number', '')
    else:
        # Fallback si viene como dict (desde api_preview)
        provider_name = _get(contract, 'provider_name', '')
        provider_rut = _get(contract, 'provider_rut', '')
        provider_profession = _get(contract, 'provider_profession', '')
        provider_nationality = _get(contract, 'provider_nationality', '')

    # ── Datos del departamento ──
    department = _get(contract, 'department', None)
    department_name = ''
    if department:
        department_name = _get(department, 'name', '')
    else:
        department_name = _get(contract, 'department_name', '')

    # ── Funciones ──
    functions_raw = _get(contract, 'functions', [])
    functions = []
    for f in functions_raw:
        if isinstance(f, str):
            functions.append(f)
        elif isinstance(f, dict):
            functions.append(f.get('description', f.get('function_description', '')))
        else:
            desc = getattr(f, 'function_description', None) or getattr(f, 'description', None) or ''
            if desc:
                functions.append(desc)

    # ── Fechas ──
    start_date = _get(contract, 'start_date', None)
    end_date = _get(contract, 'end_date', None)
    contract_date = _get(contract, 'contract_date', None)
    decline_date = _get(contract, 'decline_date', None)

    # ── Duración en meses ──
    duration_months = _get(contract, 'duration_months', None)
    if not duration_months and start_date and end_date:
        try:
            if hasattr(start_date, 'year'):
                duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        except:
            pass

    # ── Montos formateados ──
    monthly_amount = _get(contract, 'monthly_amount_gross', 0)
    total_amount = _get(contract, 'total_contract_amount', None)

    # ── Construir dict unificado ──
    context = {
        'contract_number': _get(contract, 'contract_number', 'CT-XXXX-XXX'),
        'position_title': _get(contract, 'position_title', ''),
        'program_name': _get(contract, 'program_name', ''),
        'sub_program': _get(contract, 'sub_program', ''),
        'budget_account': _get(contract, 'budget_account', ''),
        'cost_center': _get(contract, 'cost_center', ''),
        'payment_modality': _get(contract, 'payment_modality', 'MENSUAL_FIJO'),
        'decline_number': _get(contract, 'decline_number', ''),
        'decline_date': decline_date,
        'contract_date': contract_date,
        'start_date': start_date,
        'end_date': end_date,
        'monthly_amount_gross': monthly_amount,
        'total_contract_amount': total_amount,
        'duration_months': duration_months,
        'status': _get(contract, 'status', ''),

        # Prestador
        'provider_name': provider_name,
        'provider_rut': provider_rut,
        'provider_profession': provider_profession,
        'provider_nationality': provider_nationality,
        'provider_civil_status': provider_civil_status,
        'provider_address': provider_address,
        'provider_email': provider_email,
        'provider_bank_name': provider_bank_name,
        'provider_account_type': provider_account_type,
        'provider_account_number': provider_account_number,

        # Departamento
        'department_name': department_name,

        # Funciones
        'functions': functions,

        # ── Datos institucionales desde config.py ──
        'mayor_name': current_app.config.get('MAYOR_NAME', ''),
        'mayor_rut': current_app.config.get('MAYOR_RUT', ''),
        'municipality_name': current_app.config.get('MUNICIPALITY_NAME', ''),
        'municipality_short': current_app.config.get('MUNICIPALITY_SHORT', ''),
        'municipality_rut': current_app.config.get('MUNICIPALITY_RUT', ''),
        'municipality_address': current_app.config.get('MUNICIPALITY_ADDRESS', ''),
        'municipality_region': current_app.config.get('MUNICIPALITY_REGION', ''),
        'municipality_phone': current_app.config.get('MUNICIPALITY_PHONE', ''),
        'municipality_email': current_app.config.get('MUNICIPALITY_EMAIL', ''),
        'municipality_unit_name': current_app.config.get('MUNICIPALITY_UNIT_NAME', ''),
    }

    return context


def generate_contract_html(contract):
    """
    Renderiza la plantilla HTML oficial del contrato para impresión o vista previa.
    El navegador puede imprimir directamente con Ctrl+P / window.print().
    """
    context = _build_preview_context(contract)
    return render_template('contracts/preview_template.html', contract=context)


def generate_contract_pdf(contract):
    """
    Genera un PDF real a partir del HTML del contrato usando xhtml2pdf.
    Es 100% Python, no requiere instalar programas externos al sistema.

    Requiere instalar la librería:
        pip install xhtml2pdf
    """
    context = _build_preview_context(contract)
    html_string = render_template('contracts/preview_template.html', contract=context)
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


def generate_contract_preview(data_dict):
    """
    Renderiza la plantilla de previsualización con datos planos (dict).
    Se usa para la vista en vivo del armador de contratos (Split-View).
    No requiere que el contrato exista en la base de datos.
    """
    return render_template('contracts/preview_template.html', contract=data_dict)