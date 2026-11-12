# app/services/pdf_generator.py
from datetime import datetime
from flask import render_template, make_response, current_app
from xhtml2pdf import pisa
import io
import os

from app.models.decree import order_vistos


def _pdf_link_callback(uri, rel):
    """
    Resuelve rutas /static/... de las plantillas a archivos locales para que
    xhtml2pdf pueda embeber el logo municipal (si no, queda sin imagen).
    """
    try:
        if uri.startswith('/static/'):
            path = os.path.join(current_app.static_folder, uri[len('/static/'):])
            if os.path.isfile(path):
                return path
    except Exception:
        pass
    return uri


# =============================================================================
# HELPERS DE FORMATO (español, sin depender del locale del sistema)
# =============================================================================
_MONTHS_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
    7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}


def format_date_es(value):
    """Formatea una fecha (date/datetime/'YYYY-MM-DD') a español. Fallback: devolver str."""
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value  # ya viene formateada (ej: desde api_preview)
    if hasattr(value, 'month') and hasattr(value, 'year'):
        return f"{value.day} de {_MONTHS_ES[value.month]} de {value.year}"
    return str(value)


def format_money_cl(value):
    """Formatea un monto al formato chileno: 5.481.000."""
    if value in (None, ''):
        return ''
    try:
        return "{:,.0f}".format(float(value)).replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


# ── Número a palabras en español (fallback para el montol en letras) ──
_UNITS_ES = ['cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
             'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete',
             'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidós', 'veintitrés',
             'veinticuatro', 'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve']
_TENS_ES = ['', '', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
_HUNDREDS_ES = ['cero', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos',
                'seiscientos', 'setecientos', 'ochocientos', 'novecientos']


def _num_to_words_es(n, _top=False):
    """Convierte un entero (0 ≤ n < 2.000.000.000) a palabras en español."""
    if n == 0:
        return 'cero' if _top else ''
    if n < 30:
        return _UNITS_ES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _TENS_ES[d] if u == 0 else _TENS_ES[d] + ' y ' + _UNITS_ES[u]
    if n == 100:
        return 'cien'
    if n < 1000:
        c, r = divmod(n, 100)
        return _HUNDREDS_ES[c] + (' ' + _num_to_words_es(r) if r else '')
    if n < 1000000:
        miles, r = divmod(n, 1000)
        if miles == 1:
            head = 'mil'
        else:
            head = _num_to_words_es(miles).replace('veintiun', 'veintiún').replace('uno', 'un') + ' mil'
            head = head.replace('veintiun', 'veintiún')
        return head + (' ' + _num_to_words_es(r) if r else '')
    millones, r = divmod(n, 1000000)
    if millones == 1:
        head = 'un millón'
    else:
        head = _num_to_words_es(millones).replace('veintiun', 'veintiún').replace('uno', 'un') + ' millones'
    return head + (' ' + _num_to_words_es(r) if r else '')


def number_to_words_es(value):
    """Monto entero a palabras ('5481000' → 'cinco millones cuatrocientos ochenta y un mil')."""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return ''
    if n < 0 or n >= 2000000000:
        return ''
    return _num_to_words_es(n, _top=True)


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

    # ── Decretos y Antecedentes Previos (VISTOS) ──
    decrees_raw = _get(contract, 'decrees', [])
    decrees = []
    for d in decrees_raw:
        if isinstance(d, dict):
            decrees.append({
                'decree_type': d.get('decree_type', 'OTRO'),
                'decree_number': d.get('decree_number'),
                'decree_date': d.get('decree_date'),
                'description': d.get('description', ''),
            })
        else:
            decrees.append({
                'decree_type': getattr(d, 'decree_type', 'OTRO') or 'OTRO',
                'decree_number': getattr(d, 'decree_number', None),
                'decree_date': getattr(d, 'decree_date', None),
                'description': getattr(d, 'description', '') or '',
            })

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

    # ── Datos del Decreto Alcaldicio (estructura Cunco, página 2) ──
    # El domicilio/comuna del contrato (snapshot) tienen prioridad sobre la ficha.
    contract_address = _get(contract, 'provider_address', '')
    if contract_address:
        provider_address = contract_address
    provider_comuna = _get(contract, 'provider_comuna', '')
    try:
        hours_weekly = int(_get(contract, 'hours_weekly', None) or 0) or None
    except (TypeError, ValueError):
        hours_weekly = None
    if not hours_weekly:
        hours_weekly = 44  # Jornada estándar Cunco

    try:
        total_amount_formatted = format_money_cl(total_amount)
    except Exception:
        total_amount_formatted = ''
    if not total_amount:
        total_amount_formatted = ''

    total_amount_words = _get(contract, 'total_amount_words', '')
    if not total_amount_words and total_amount:
        auto_words = number_to_words_es(total_amount)
        if auto_words:
            total_amount_words = auto_words

    budget_year = None
    if start_date and hasattr(start_date, 'year'):
        budget_year = start_date.year
    if (not budget_year) and isinstance(start_date, str) and len(start_date) >= 4:
        try:
            budget_year = int(start_date[:4])
        except ValueError:
            budget_year = None
    if not budget_year:
        budget_year = datetime.now().year

    # ── Fechas en español ──
    contract_date_es = format_date_es(contract_date) or format_date_es(start_date)
    start_date_es = format_date_es(start_date)
    end_date_es = format_date_es(end_date)
    decline_date_es = format_date_es(decline_date)

    # ── VISTOS: filtrados y ordenados por decreto_type (bloque página 1) ──
    vistos = order_vistos(decrees)

    # ── Firmas ágiles (rúbrica) con metadatos de validación ──
    signatures_raw = _get(contract, 'signatures', []) or []
    signatures = []
    for s in signatures_raw:
        if isinstance(s, dict):
            signatures.append(s)
        else:
            signatures.append({
                'id': getattr(s, 'id', None),
                'signer_name': getattr(s, 'signer_name', '') or '',
                'signer_rut': getattr(s, 'signer_rut', '') or '',
                'signer_role': getattr(s, 'signer_role', '') or '',
                'signed_at': getattr(s, 'signed_at', None),
                'ip_address': getattr(s, 'ip_address', None) or getattr(s, 'ip', None),
                'device_type': getattr(s, 'device_type', None),
                'document_hash': getattr(s, 'document_hash', None) or getattr(s, 'document_hash_sha256', None),
                'signature_image': getattr(s, 'signature_image', None) or getattr(s, 'signature_data', None),
                'validation_code': getattr(s, 'validation_code', '') or '',
            })
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
        # Fechas en español (Decreto Alcaldicio)
        'decline_date_es': decline_date_es,
        'contract_date_es': contract_date_es,
        'start_date_es': start_date_es,
        'end_date_es': end_date_es,
        'monthly_amount_gross': monthly_amount,
        'total_contract_amount': total_amount,
        'total_amount_formatted': total_amount_formatted,
        'total_amount_words': total_amount_words,
        'duration_months': duration_months,
        'status': _get(contract, 'status', ''),

        # Prestador
        'provider_name': provider_name,
        'provider_rut': provider_rut,
        'provider_profession': provider_profession,
        'provider_nationality': provider_nationality,
        'provider_civil_status': provider_civil_status,
        'provider_address': provider_address,
        'provider_comuna': provider_comuna,
        'hours_weekly': hours_weekly,
        'budget_year': budget_year,
        'provider_email': provider_email,
        'provider_bank_name': provider_bank_name,
        'provider_account_type': provider_account_type,
        'provider_account_number': provider_account_number,

        # Departamento
        'department_name': department_name,

        # Funciones
        'functions': functions,

        # ── Firmas del Decreto (dataURL PNG o None) ──
        'mayor_signature': _get(contract, 'mayor_signature', None),
        'secretary_signature': _get(contract, 'secretary_signature', None),

        # ── Firmas ágiles (rúbrica) ──
        'signatures': signatures,

        # Decretos y Antecedentes Previos (VISTOS)
        'decrees': decrees,
        # VISTOS filtrados + ordenados por decreto_type (bloque página 1)
        'vistos': vistos,

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

    # Generar PDF en memoria (link_callback para resolver imágenes /static/)
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer, link_callback=_pdf_link_callback)

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