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
# PARSER INTELIGENTE DE DATOS DE CONTRATO
# =============================================================================

_MONTHS_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}


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

    # ── RUT chileno ──────────────────────────────────────────────────────────
    rut_patterns = [
        r'\b(\d{1,2}(?:\.\d{3}){2}-[\dkK])\b',
        r'\b(\d{7,8}-[\dkK])\b',
        r'cédula de identidad N°?\s*([\d\.kK-]+)',
        r'rut[:\s]*([\d\.kK-]+)',
    ]
    for pattern in rut_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            rut = match.group(1).replace('.', '').upper()
            if len(rut) >= 9:
                data['rut'] = rut
                break

    # ── Nombre del prestador ─────────────────────────────────────────────────
    name_patterns = [
        r'[Dd]on\(a\)?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
        r'[Yy]\s+[Dd]on\(a\)?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
        r'prestador\s+(?:será\s+)?(?:el\s+)?(?:señor\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, full_text)
        if match:
            name = match.group(1).strip()
            if len(name) > 5 and not any(x in name.lower() for x in ['municipalidad', 'alcalde', 'república']):
                data['full_name'] = name
                break

    # ── Cargo / Posición ─────────────────────────────────────────────────────
    cargo_patterns = [
        r'(?:cargo|desempeñará)\s+(?:el\s+)?(?:cargo\s+)?(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{5,50}?)(?=\s+(?:en\s+el|en\s+la|en\s+|el\s+departamento|la\s+unidad|\.|,))',
        r'(?:técnico|profesional|asesor|coordinador|apoyo|auxiliar|jefe|secretaría|encargad[oa])\s+(?:en\s+)?(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóúñÑ\s]{3,40})',
    ]
    for pattern in cargo_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            cargo = match.group(0).strip()
            # Limpiar prefijos
            cargo = re.sub(r'^(cargo|desempeñará|el|de)\s+', '', cargo, flags=re.IGNORECASE).strip()
            if len(cargo) > 3:
                data['position_title'] = cargo.title()
                break

    # ── Programa Municipal ───────────────────────────────────────────────────
    prog_match = re.search(r'(?:programa|proyecto)\s+(?:municipal\s+)?["\']?([A-Za-zÁÉÍÓÚáéíóúñÑ\s\d]+?)["\']?(?=\.|,|en\s+el|del)', full_text, re.IGNORECASE)
    if prog_match:
        prog = prog_match.group(1).strip()
        if len(prog) > 3 and len(prog) < 80:
            data['program_name'] = prog.title()

    # ── Monto mensual ────────────────────────────────────────────────────────
    amount_patterns = [
        r'\$\s*([\d\.]+(?:\.\d{3})*)\s*(?:pesos|clp)',
        r'(?:monto|renta|honorario|valor)\s+(?:mensual|bruto)?\s*(?:de\s+)?\$?\s*([\d\.]+(?:\.\d{3})*)',
        r'([\d\.]{3,}(?:\.\d{3})*)\s*(?:pesos chilenos|pesos\s*\(?clp\)?|clp)',
        r'\$\s*([\d\.]+)',
    ]
    for pattern in amount_patterns:
        matches = re.findall(pattern, full_text_lower)
        for m in matches:
            clean = m.replace('.', '').replace(',', '')
            if clean.isdigit() and int(clean) >= 10000:
                data['monthly_amount_gross'] = float(clean)
                break
        if data['monthly_amount_gross']:
            break

    # ── Fechas ───────────────────────────────────────────────────────────────
    dates_found = []

    # Formato: "10 de agosto de 2026"
    date_pattern_1 = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december)\s+de\s+(\d{4})'
    for match in re.finditer(date_pattern_1, full_text_lower):
        try:
            day, month_str, year = match.groups()
            month = _MONTHS_ES.get(month_str.lower())
            if month:
                dates_found.append(datetime(int(year), month, int(day)))
        except:
            pass

    # Formato: "10/08/2026" o "2026-08-10"
    date_pattern_2 = r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b'
    for match in re.finditer(date_pattern_2, full_text):
        try:
            d1, d2, year = match.groups()
            year = int(year)
            # Asumir DD/MM/YYYY (formato chileno)
            d = datetime(year, int(d2), int(d1))
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
        r'(?:decreto|dec\.?)(?:\s+alcaldicio)?(?:\s+n°?)?\s*([A-Za-z0-9\-]+)',
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
        r'(?:contrato|ct)[\s\.\-]+n°?\s*([A-Za-z0-9\-]+)',
        r'(?:n°|número)\s*(CT[\s\.\-]+\d+(?:[\s\.\-]+\d+)?)',
    ]
    for pattern in contract_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            data['contract_number'] = match.group(1).strip().upper()
            break

    # ── Departamento ─────────────────────────────────────────────────────────
    dept_patterns = [
        r'(?:departamento|dirección|unidad)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\.|,|en\s+el|el\s+cargo)',
        r'(?:en\s+el\s+departamento|en\s+la\s+dirección|en\s+la\s+unidad)\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)(?=\.|,|en\s+el)',
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
    function_keywords = ['funciones', 'cometidos', 'deberes', 'tareas', 'actividades específicas', 'serán funciones']
    end_keywords = ['tercero:', 'cuarto:', 'quinto:', 'sexto:', 'en todo lo no previsto', 
                    'monto', 'honorario', 'plazo', 'vigencia', 'duración', 'renta', 'pago']

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
            # Evitar líneas que son solo encabezados
            if clean and len(clean) > 10 and len(clean) < 300:
                # Evitar duplicados y líneas que claramente no son funciones
                bad_words = ['república', 'municipalidad', 'contrato', 'prestación', 
                           'honorarios', 'rut:', 'cédula', 'alcalde', 'decreto']
                if not any(bad in clean.lower() for bad in bad_words):
                    if clean not in functions:
                        functions.append(clean)

            if len(functions) >= 15:
                break

    # Fallback: si no encontramos sección específica, buscar líneas numeradas con contenido descriptivo
    if not functions:
        for line in lines:
            clean = re.sub(r'^[\d\.\)\-\•\–\—\*]+\s*', '', line).strip()
            if clean and 20 < len(clean) < 200:
                bad_words = ['república', 'municipalidad', 'contrato', 'prestación', 
                           'honorarios', 'rut:', 'cédula', 'alcalde', 'decreto', 'primero:', 'segundo:']
                if not any(bad in clean.lower() for bad in bad_words):
                    if clean not in functions:
                        functions.append(clean)
            if len(functions) >= 10:
                break

    return functions