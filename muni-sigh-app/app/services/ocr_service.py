import os
import re
import pdfplumber
from paddleocr import PaddleOCR
import logging
from datetime import datetime

# Inicializar PaddleOCR (solo idioma español)
ocr_engine = PaddleOCR(use_angle_cls=True, lang='es')


def extract_text_from_pdf(file_path: str) -> str:
    """
    Intenta extraer texto de un PDF de forma nativa. 
    Si no encuentra texto suficiente (probablemente un documento escaneado), 
    aplica OCR a las páginas.
    """
    extracted_text = ""
    needs_ocr = False

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

            # Si el texto extraído es muy corto, asumimos que es una imagen escaneada
            if len(extracted_text.strip()) < 50:
                needs_ocr = True

        if needs_ocr:
            extracted_text = _extract_via_ocr(file_path)

        return extracted_text.strip()

    except Exception as e:
        logging.error(f"Error procesando PDF {file_path}: {str(e)}")
        raise e


def _extract_via_ocr(file_path: str) -> str:
    """Aplica PaddleOCR convirtiendo el PDF en imágenes temporalmente."""
    ocr_text = ""

    result = ocr_engine.ocr(file_path, cls=True)

    for page_result in result:
        if page_result:
            for line in page_result:
                ocr_text += line[1][0] + " "
            ocr_text += "\n"

    return ocr_text


# =============================================================================
# FORMATO DE FECHAS EN ESPAÑOL (sin depender del locale del sistema)
# =============================================================================

_MONTHS_ES_LIST = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

_MONTHS_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}


def format_date_es(date_input) -> str:
    """
    Formatea una fecha a texto en español, sin depender del locale del sistema.
    Acepta: datetime, date, str ('YYYY-MM-DD'), o None.
    """
    if not date_input:
        return '___ de ________ de ____'
    
    try:
        if isinstance(date_input, str):
            date_input = datetime.strptime(date_input, '%Y-%m-%d').date()
        elif isinstance(date_input, datetime):
            date_input = date_input.date()
        
        day = date_input.day
        month = _MONTHS_ES_LIST[date_input.month - 1]
        year = date_input.year
        return f'{day} de {month} de {year}'
    except Exception:
        return str(date_input)


# =============================================================================
# PARSER INTELIGENTE DE DATOS DE CONTRATO
# =============================================================================

def parse_contract_data(text: str) -> dict:
    """
    Analiza texto extraído de un contrato a honorarios y extrae datos estructurados.
    Devuelve un dict con los campos detectados para autocompletar el formulario.
    """
    data = {
        'rut': None,
        'full_name': None,
        'position_title': None,
        'program_name': None,
        'monthly_amount_gross': None,
        'total_contract_amount': None,
        'start_date': None,
        'end_date': None,
        'decline_number': None,
        'decline_date': None,
        'contract_number': None,
        'functions': [],
        'department_name': None,
        'raw_text': text
    }

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    full_text_lower = text.lower()
    full_text = text

    # ── RUT chileno (más permisivo con errores OCR) ──────────────────────────
    rut_patterns = [
        r'\b(\d{1,2}(?:\.\d{3}){2}-[\dkK])\b',
        r'\b(\d{7,8}-[\dkK])\b',
        r'c[eé]dula\s+de\s+identidad\s+N[°o]?\s*([\d\.\-kK]+)',
        r'c[eé]dula\s+identidad\s+N[°o]?\s*([\d\.\-kK]+)',
        r'identidad\s+N[°o]?\s*([\d\.\-kK]+)',
        r'rut[:\s]*([\d\.\-kK]+)',
    ]
    for pattern in rut_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            rut_raw = match.group(1).replace('.', '').replace(' ', '').upper()
            # Validar formato RUT chileno básico
            if len(rut_raw) >= 9 and '-' in rut_raw:
                data['rut'] = rut_raw
                break

    # ── Nombre del prestador (más permisivo) ─────────────────────────────────
    # Buscar después de "Don(a)" o "y Don(a)" o "prestador será"
    name_patterns = [
        r'[Dd]on\s*\(?a\)?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+){1,4})',
        r'[Yy]\s+[Dd]on\s*\(?a\)?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+){1,4})',
        r'prestador\s+(?:ser[aá]\s+)?(?:el\s+)?(?:señor\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+){1,4})',
        r'entre\s+la\s+I\.\s*MUNICIPALIDAD[^,]+,\s+y\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ]+){1,4})',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, full_text)
        if match:
            name = match.group(1).strip()
            # Filtrar nombres inválidos
            invalid = ['municipalidad', 'alcalde', 'república', 'chile', 'temuco', 
                      'contrato', 'prestación', 'servicios', 'honorarios']
            if len(name) > 5 and not any(inv in name.lower() for inv in invalid):
                data['full_name'] = name
                break

    # ── Cargo / Posición (mejorado para cláusula PRIMERO) ────────────────────
    cargo_patterns = [
        r'PRIMERO:?\s+El\s+prestador\s+desempeñará\s+el\s+cargo\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\s+en\s+el\s+departamento|\s+en\s+la\s+unidad|\s+en\s+el\s+área)',
        r'cargo\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,60}?)(?=\s+en\s+el|\s+en\s+la|\s+en\s+|\.|,)',
        r'desempeñará\s+el\s+cargo\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,60}?)(?=\s+en\s+el|\s+en\s+la|\s+en\s+|\.|,)',
        r'(?:técnico|profesional|asesor|coordinador|apoyo|auxiliar|jefe|secretaría|encargad[oa]|analista)\s+(?:en\s+)?(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,50})',
    ]
    for pattern in cargo_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            cargo = match.group(1).strip()
            # Limpiar prefijos comunes
            cargo = re.sub(r'^(cargo|desempeñará|el|de|de\s+la|de\s+los|de\s+las)\s+', '', cargo, flags=re.IGNORECASE).strip()
            if len(cargo) > 3:
                data['position_title'] = cargo.title()
                break

    # ── Programa Municipal ───────────────────────────────────────────────────
    prog_patterns = [
        r'programa\s+municipal\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s\d]+?)(?=\.|,|\s+en\s+el|\s+del\s+)',
        r'programa\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s\d]+?)(?=\.|,|\s+en\s+el|\s+del\s+)',
        r'marco\s+del\s+programa\s+(?:municipal\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ\s\d]+?)(?=\.|,)',
    ]
    for pattern in prog_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            prog = match.group(1).strip()
            if len(prog) > 3 and len(prog) < 80:
                data['program_name'] = prog.title()
                break

    # ── Monto mensual (mejorado para formato chileno) ────────────────────────
    amount_patterns = [
        r'\$\s*([\d\.]+(?:\.\d{3})*)\s*(?:pesos|clp)',
        r'(?:monto|renta|honorario|valor)\s+(?:mensual|bruto)?\s*(?:de\s+)?\$?\s*([\d\.]+(?:\.\d{3})*)',
        r'([\d\.]{3,}(?:\.\d{3})*)\s*(?:pesos chilenos|pesos\s*\(?clp\)?|clp)',
        r'renta\s+bruta\s+mensual\s+(?:acordada\s+)?(?:es\s+)?(?:de\s+)?\$?\s*([\d\.]+)',
        r'\$\s*([\d\.]+)',
    ]
    for pattern in amount_patterns:
        matches = re.findall(pattern, full_text_lower)
        for m in matches:
            clean = m.replace('.', '').replace(',', '').replace(' ', '')
            if clean.isdigit() and int(clean) >= 10000:
                data['monthly_amount_gross'] = float(clean)
                break
        if data['monthly_amount_gross']:
            break

    # ── Fechas (más robusto) ─────────────────────────────────────────────────
    dates_found = []

    # Formato: "10 de agosto de 2026"
    date_pattern_1 = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december|ene|feb|mar|abr|jun|jul|ago|sep|oct|nov|dic)\s+de\s+(\d{4})'
    for match in re.finditer(date_pattern_1, full_text_lower):
        try:
            day, month_str, year = match.groups()
            month = _MONTHS_ES.get(month_str.lower())
            if month:
                dates_found.append(datetime(int(year), month, int(day)))
        except:
            pass

    # Formato: "10/08/2026" (DD/MM/YYYY chileno)
    date_pattern_2 = r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'
    for match in re.finditer(date_pattern_2, full_text):
        try:
            day, month, year = match.groups()
            d = datetime(int(year), int(month), int(day))
            dates_found.append(d)
        except:
            pass

    # Formato ISO: "2026-08-10"
    date_pattern_3 = r'\b(\d{4})-(\d{2})-(\d{2})\b'
    for match in re.finditer(date_pattern_3, full_text):
        try:
            year, month, day = match.groups()
            dates_found.append(datetime(int(year), int(month), int(day)))
        except:
            pass

    dates_found = sorted(list(set(dates_found)))
    if len(dates_found) >= 2:
        data['start_date'] = dates_found[0].strftime('%Y-%m-%d')
        data['end_date'] = dates_found[-1].strftime('%Y-%m-%d')
    elif len(dates_found) == 1:
        data['start_date'] = dates_found[0].strftime('%Y-%m-%d')

    # ── Decreto Alcaldicio ───────────────────────────────────────────────────
    decree_patterns = [
        r'(?:decreto|dec\.?)\s+(?:alcaldicio\s+)?N[°o]?\s*([A-Za-z0-9\-]+)',
        r'Decreto\s+Alcaldicio\s+N[°o]?\s*([A-Za-z0-9\-]+)',
        r'decree\s*(?:n°?)?\s*([A-Za-z0-9\-]+)',
    ]
    for pattern in decree_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            dec = match.group(1).strip()
            if len(dec) >= 2:
                data['decline_number'] = dec.upper()
                break

    # ── Número de contrato ───────────────────────────────────────────────────
    contract_patterns = [
        r'(?:contrato|ct)[\s\.\-]+N[°o]?\s*([A-Za-z0-9\-]+)',
        r'N[°o]?\s*(CT[\s\.\-]+\d+(?:[\s\.\-]+\d+)?)',
        r'Contrato\s+N[°o]?\s*([A-Za-z0-9\-]+)',
    ]
    for pattern in contract_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            data['contract_number'] = match.group(1).strip().upper()
            break

    # ── Departamento ─────────────────────────────────────────────────────────
    dept_patterns = [
        r'(?:departamento|dirección|unidad)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\s*,|\s*\.|\s+en\s+el|\s+el\s+cargo)',
        r'(?:en\s+el\s+departamento|en\s+la\s+dirección|en\s+la\s+unidad)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\s*,|\s*\.|\s+en\s+el)',
        r'departamento\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\s*,|\s*\.)',
    ]
    for pattern in dept_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            dept = match.group(1).strip()
            if len(dept) > 3 and len(dept) < 50:
                data['department_name'] = dept.title()
                break

    # ── Funciones ────────────────────────────────────────────────────────────
    data['functions'] = extract_functions(text)

    return data


def extract_functions(text: str) -> list:
    """
    Extrae la lista de funciones/cometidos del texto del contrato.
    Busca listas numeradas o bullets después de palabras clave de sección.
    """
    functions = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Buscar sección de funciones
    in_functions = False
    function_keywords = ['funciones', 'cometidos', 'deberes', 'tareas', 
                        'actividades específicas', 'serán funciones', 'segundo:']
    end_keywords = ['tercero:', 'cuarto:', 'quinto:', 'sexto:', 'séptimo:', 'octavo:',
                    'en todo lo no previsto', 'monto', 'honorario', 'plazo', 
                    'vigencia', 'duración', 'renta', 'pago', 'el presente contrato']

    for i, line in enumerate(lines):
        lower = line.lower()

        # Detectar inicio de sección de funciones
        if any(kw in lower for kw in function_keywords) and not in_functions:
            in_functions = True
            continue

        if in_functions:
            # Detectar fin de sección
            if any(kw in lower for kw in end_keywords) and len(functions) > 0:
                break

            # Líneas numeradas o con bullets
            clean = re.sub(r'^[\d\.\)\-\•\–\—\*]+\s*', '', line).strip()
            
            # Evitar líneas que son solo encabezados o irrelevantes
            if clean and len(clean) > 10 and len(clean) < 300:
                bad_words = ['república', 'municipalidad', 'contrato', 'prestación', 
                           'honorarios', 'rut:', 'cédula', 'alcalde', 'decreto',
                           'primero:', 'segundo:', 'tercero:', 'cuarto:']
                if not any(bad in clean.lower() for bad in bad_words):
                    if clean not in functions:
                        functions.append(clean)

            if len(functions) >= 15:
                break

    # Fallback: si no encontramos sección específica
    if not functions:
        for line in lines:
            clean = re.sub(r'^[\d\.\)\-\•\–\—\*]+\s*', '', line).strip()
            if clean and 20 < len(clean) < 200:
                bad_words = ['república', 'municipalidad', 'contrato', 'prestación', 
                           'honorarios', 'rut:', 'cédula', 'alcalde', 'decreto', 
                           'primero:', 'segundo:', 'tercero:']
                if not any(bad in clean.lower() for bad in bad_words):
                    if clean not in functions:
                        functions.append(clean)
            if len(functions) >= 10:
                break

    return functions