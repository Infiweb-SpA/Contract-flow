import os
# 1. Estas variables deben ir ANTES de importar paddleocr para desactivar el modo que crashea en Windows
os.environ['FLAGS_enable_pir_in_executor'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

import re
import io
import logging
from datetime import datetime

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR


# =============================================================================
# EXCEPCIÓN DE CANCELACIÓN
# =============================================================================

class OCRCancelledException(Exception):
    """Se lanza cuando el procesamiento OCR es cancelado por el usuario."""
    pass


# 2. Desactivar oneDNN (enable_mkldnn=False)
ocr_engine = PaddleOCR(
    lang='es',
    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    enable_mkldnn=False
)


def extract_text_from_pdf(file_path: str, is_cancelled=None) -> str:
    """
    Intenta extraer texto de un PDF de forma nativa.
    Si no encuentra texto suficiente (probablemente un documento escaneado),
    aplica OCR a las páginas convirtiéndolas a imagen primero.

    Args:
        file_path: Ruta al archivo PDF.
        is_cancelled: Callable opcional que retorna True si el procesamiento
                      debe ser cancelado. Se verifica entre cada página del OCR.
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
            extracted_text = _extract_via_ocr(file_path, is_cancelled=is_cancelled)

        return extracted_text.strip()

    except OCRCancelledException:
        raise
    except Exception as e:
        logging.error(f"Error procesando PDF {file_path}: {str(e)}")
        raise e


def _extract_via_ocr(file_path: str, is_cancelled=None) -> str:
    """
    Aplica PaddleOCR 3.x convirtiendo el PDF en imágenes con PyMuPDF.

    Args:
        file_path: Ruta al archivo PDF.
        is_cancelled: Callable opcional que se invoca entre cada página.
                      Si retorna True, se detiene el procesamiento inmediatamente.
    """
    ocr_text = ""

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logging.error(f"No se pudo abrir el PDF con PyMuPDF {file_path}: {e}")
        return ""

    total_pages = len(doc)
    print(f"--> Iniciando OCR para {total_pages} páginas...")

    try:
        for page_index in range(total_pages):
            # ── Verificar cancelación antes de procesar cada página ──
            if is_cancelled and is_cancelled():
                print(f"    ✗ OCR cancelado por el usuario en página {page_index + 1}/{total_pages}")
                # NO cerrar doc aquí — el finally se encarga de eso.
                # Solo lanzar la excepción de cancelación.
                raise OCRCancelledException(
                    f"Procesamiento OCR cancelado en página {page_index + 1} de {total_pages}"
                )

            print(f"    - Procesando página {page_index + 1}/{total_pages}...")
            try:
                page = doc.load_page(page_index)
                zoom = 1.5
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                img_data = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                img_array = np.array(pil_img)

                result_gen = ocr_engine.predict(input=img_array)

                if not isinstance(result_gen, list):
                    results = list(result_gen)
                else:
                    results = result_gen

                if results and len(results) > 0:
                    page_res = results[0]

                    texts = []
                    if hasattr(page_res, 'rec_texts'):
                        texts = page_res.rec_texts
                    elif isinstance(page_res, dict) and 'rec_texts' in page_res:
                        texts = page_res['rec_texts']

                    lines_count = 0
                    for t in texts:
                        if t and t.strip():
                            ocr_text += t.strip() + "\n"
                            lines_count += 1
                    print(f"      ✓ Texto extraído en página {page_index + 1}: {lines_count} líneas")

            except OCRCancelledException:
                raise
            except Exception as page_err:
                logging.error(f"Error OCR en página {page_index}: {page_err}")
                continue
        print("--> OCR finalizado.")
    finally:
        # Cerrar el documento de forma segura (puede ya estar cerrado)
        try:
            doc.close()
        except Exception:
            pass

    return ocr_text.strip()


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
# HELPERS NUEVOS
# =============================================================================

def _try_match(text: str, patterns: list, flags=re.IGNORECASE):
    """
    Intenta múltiples regex contra el texto y devuelve el primer match encontrado.
    Permite tener patrones primarios y de fallback para cada campo.
    """
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if m:
            return m
    return None


def _normalize_amount(raw: str):
    """
    Convierte un string de monto (con puntos, comas, espacios) a entero.
    Ej: '5.481.000' → 5481000, '$ 913.500' → 913500
    """
    if not raw:
        return None
    cleaned = re.sub(r'[^\d]', '', raw.strip())
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_any_date(date_str: str) -> str:
    """
    Convierte CUALQUIER formato de fecha encontrado en el OCR a ISO YYYY-MM-DD.
    Soporta: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD de mes de YYYY, YYYY/MM/DD
    """
    if not date_str:
        return None
    date_str = date_str.strip()

    # YYYY-MM-DD
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # DD de mes de YYYY (ej: "30 de junio de 2026")
    m = re.search(r'(\d{1,2})\s+de\s+([a-zA-Záéíóú]+)\s+de\s+(\d{4})', date_str, re.IGNORECASE)
    if m:
        day, month_name, year = m.groups()
        month = _MONTHS_ES.get(month_name.lower().strip(), 1)
        return f"{int(year):04d}-{month:02d}-{int(day):02d}"

    # YYYY/MM/DD
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    return date_str


# =============================================================================
# PARSER INTELIGENTE DE DATOS DE CONTRATO (REESCRITO)
# =============================================================================

def parse_contract_data(text: str) -> dict:
    """
    Analiza texto extraído de un contrato a honorarios municipal y extrae datos estructurados.
    Retorna un diccionario mapeado para auto-completar el formulario/contexto.

    V3: Regex reescritos con múltiples patrones de fallback para manejar
    la variabilidad real de contratos municipales chilenos.
    """
    data = {
        # Prestador
        'rut': None,
        'full_name': None,
        'provider_profession': None,
        'provider_nationality': None,
        'provider_address': None,
        'provider_email': None,

        # Objeto y Estructura
        'position_title': None,
        'program_name': None,
        'sub_program': None,
        'department_name': None,

        # Presupuesto y Pagos
        'monthly_amount_gross': None,
        'total_contract_amount': None,
        'budget_account': None,
        'cost_center': None,
        'payment_modality': 'MENSUAL_FIJO',

        # Fechas y Documentos
        'start_date': None,
        'end_date': None,
        'contract_date': None,
        'decline_number': None,
        'decline_date': None,
        'contract_number': None,

        # Funciones
        'functions': [],
        'raw_text': text
    }

    full_text = text

    # ── 1. NÚMERO DE CONTRATO ──────────────────────────────────────────────
    match_ct = _try_match(full_text, [
        r'(?:N[°oº\.]*\s*)(CT-\d{4}-\d{3,6})',
        r'(?:N[°oº\.]*\s*)(CH-\d{4}-\d{3,6})',
        r'(CT-\d{4}-\d{3,6})',
        r'(CH-\d{4}-\d{3,6})',
        r'(?:Contrato\s+(?:N[°oº\.]*\s*)?)(\w{2,4}-\d{4}-\d{3,6})',
    ])
    if match_ct:
        data['contract_number'] = match_ct.group(1).upper().strip()

    # ── 2. DECRETO ALCALDICIO (INTELIGENTE) ────────────────────────────────
    match_dec = _try_match(full_text, [
        r'(?:DECRETO\s+ALCALDICIO|Decreto\s+Alcaldicio)\s+N[°oº\.\s]*\s*(\d+)[\s\S]{0,200}?(?:APRUEBA|Aprueba|aprueba)',
        r'(?:DECRETO\s+ALCALDICIO|Decreto\s+Alcaldicio)\s+N[°oº\.\s]*\s*(\d+)\s*(?:,\s*|\s+de\s+fecha\s+|\s+del?\s+)([\d\-/]{8,12})',
        r'(?:DECRETO\s+ALCALDICIO|Decreto\s+Alcaldicio)\s+N[°oº\.\s]*\s*(\d+)',
        r'(?:D\.A\.|DA)\s+N[°oº\.]*\s*(\d+)',
    ])
    if match_dec:
        data['decline_number'] = match_dec.group(1)
        if match_dec.lastindex >= 2 and match_dec.group(2):
            data['decline_date'] = _parse_any_date(match_dec.group(2))

    # ── 3. FECHA DEL DOCUMENTO ─────────────────────────────────────────────
    match_doc_date = _try_match(full_text, [
        r'(?:En\s+la\s+comuna\s+de\s+\w+),?\s+a\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        r'(?:[A-Z]{2,}),?\s+a\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        r'[Ff]echa\s+de\s+firma\s*:\s*(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        r'[Ff]echa\s+de\s+firma\s*:\s*([\d\-/]{8,12})',
    ])
    if match_doc_date:
        parsed_date = _parse_any_date(match_doc_date.group(1))
        if not data['contract_date']:
            data['contract_date'] = parsed_date
        if not data['decline_date']:
            data['decline_date'] = parsed_date

    # ── 4. PRESTADOR (nombre + RUT) ────────────────────────────────────────
    match_prestador = _try_match(full_text, [
        r'don(?:$$[^)]*$$)?\s+([^,]+?)(?:,\s*de\s+nacionalidad\s+\w+)?,\s*(?:[Cc]édula\s+(?:Nacional\s+de\s+)?[Ii]dentidad)\s*(?:N?[°oº\.:\s]+)\s*([\d\.\-\s]+[kK]?)',
        r'don(?:$$[^)]*$$)?\s+([^,]+),\s*[Rr](?:\.?U\.?T\.?|ut)\s*(?::?\s*N?[°oº\.:\s]*)\s*([\d\.\-\s]+[kK]?)',
        r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]+?),\s*(?:R\.?U\.?T\.?|CI)\s*(?:N?[°oº\.:\s]*)\s*([\d\.\-\s]+[kK]?)',
    ])
    if match_prestador:
        data['full_name'] = re.sub(r'\s+', ' ', match_prestador.group(1).strip()).title()
        data['rut'] = re.sub(r'\s', '', match_prestador.group(2)).strip().upper()

    # ── 5. PROGRAMA ────────────────────────────────────────────────────────
    match_prog = _try_match(full_text, [
        r'programa\s+(?:denominado\s+)?["""\']?([^"""\',\.]+)',
        r'Programa\s+["""\']?([^"""\',\.]+)',
        r'programa\s+municipal\s+([^,\.]+)',
    ])
    if match_prog:
        data['program_name'] = match_prog.group(1).strip()

    # ── 6. SUBPROGRAMA ─────────────────────────────────────────────────────
    match_sub = _try_match(full_text, [
        r'subprograma\s+([^,\.]+)',
    ])
    if match_sub:
        data['sub_program'] = match_sub.group(1).strip()

    # ── 7. DEPARTAMENTO ────────────────────────────────────────────────────
    match_dept = _try_match(full_text, [
        r'de\s+la\s+(ADMINISTRACI[ÓO]N\s+MUNICIPAL)',
        r'(?:dependiente\s+de\s+la|de\s+la)\s+((?:DIRECCI[ÓO]N|UNIDAD)\s+DE\s+[A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+)*)',
        r'(?:dependiente\s+de\s+la|de\s+la)\s+((?:Dirección|Unidad)\s+de\s+[A-Za-záéíóúñ]+(?:\s+[A-Za-záéíóúñ]+)*)',
    ])
    if match_dept:
        data['department_name'] = match_dept.group(1).strip().title()

    # ── 8. CARGO / POSICIÓN ────────────────────────────────────────────────
    match_pos = _try_match(full_text, [
        r'servicio\s+de\s+([^,\.]+?)(?:,|\s+para\s+)',
        r'(?:cargo|puesto)\s+(?:de\s+)?([^,\.]+)',
    ])
    if match_pos:
        data['position_title'] = match_pos.group(1).strip().capitalize()

    # ── 9. PRESUPUESTO ─────────────────────────────────────────────────────
    match_budget = _try_match(full_text, [
        r'[ÍI]tem\s+([\d\.]+)\s+del\s+Presupuesto',
        r'cuenta\s+presupuestaria\s+(?:N?[°oº\.]*\s*)?([\d\.\-]+)',
        r'imputaci[óo]n\s+presupuestaria[^\d]*([\d\.\-]+)',
    ])
    if match_budget:
        data['budget_account'] = match_budget.group(1).strip()

    match_centro = _try_match(full_text, [
        r'centro\s+de\s+costo\s+(?:N?[°oº\.]*\s*)?([\d\.\-]+)',
    ])
    if match_centro:
        data['cost_center'] = match_centro.group(1).strip()

    # ── 10. VIGENCIA (fechas inicio y término) ─────────────────────────────
    match_vigencia = _try_match(full_text, [
        r'(?:regir[áa]|vigencia|duraci[óo]n|regir[áa])\s+desde\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\s+(?:hasta\s+(?:el\s+)?|al\s+)(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
        r'(?:regir[áa]|vigencia|duraci[óo]n)\s+desde\s+(?:el\s+)?([\d\-/]{8,12})\s+(?:hasta\s+(?:el\s+)?|al\s+)([\d\-/]{8,12})',
        r'desde\s+(?:el\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\s+(?:hasta\s+(?:el\s+)?|al\s+)(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})',
    ])
    if match_vigencia:
        data['start_date'] = _parse_any_date(match_vigencia.group(1))
        data['end_date'] = _parse_any_date(match_vigencia.group(2))

    # ── 11. MONTOS ─────────────────────────────────────────────────────────
    match_total = _try_match(full_text, [
        r'suma\s+(?:[úu]nica\s+y\s+)?total\s+(?:de\s+)?\$\s*([\d\.\,]+)',
        r'monto\s+total\s+(?:del\s+)?contrato[^\$]*\$\s*([\d\.\,]+)',
        r'(?:monto|valor)\s+total[^\$]*\$\s*([\d\.\,]+)',
    ])
    if match_total:
        data['total_contract_amount'] = _normalize_amount(match_total.group(1))

    match_monto = _try_match(full_text, [
        r'\d+\s*cuota[^\$]*\$\s*([\d\.\,]+)',
        r'renta\s+bruta\s+mensual[^\$]*\$\s*([\d\.\,]+)',
        r'(?:monto|honorario)\s+(?:bruto\s+)?mensual[^\$]*\$\s*([\d\.\,]+)',
    ])
    if match_monto:
        data['monthly_amount_gross'] = _normalize_amount(match_monto.group(1))

    if 'producto o servicio entregado' in full_text.lower():
        data['payment_modality'] = 'POR_PRODUCTO'

    # ── 12. FUNCIONES ──────────────────────────────────────────────────────
    data['functions'] = extract_functions(full_text)

    # ── DEBUG: Log de campos extraídos ─────────────────────────────────────
    extracted_fields = {k: v for k, v in data.items() if v is not None and k not in ('raw_text', 'functions')}
    logging.info(f"OCR Parser: {len(extracted_fields)} campos extraídos: {list(extracted_fields.keys())}")
    if data['functions']:
        logging.info(f"OCR Parser: {len(data['functions'])} funciones extraídas")

    return data


def _parse_date_string(date_str: str) -> str:
    """Helper interno para convertir cualquier variante de fecha a ISO YYYY-MM-DD."""
    return _parse_any_date(date_str)


def extract_functions(text: str) -> list:
    """
    Extrae funciones/cometidos del contrato.
    V3: Soporta listas numeradas (1. 2. 3.), con guiones (- item),
    y bullets (• item). Maneja items multi-línea.
    """
    functions = []

    match_sec = _try_match(text, [
        r'(?:Ser[áa]n\s+)?funciones\s+(?:espec[íi]ficas\s+)?(?:del\s+Prestador\s+)?las\s+siguientes\s*:\s*(.*?)(?:El\s+Prestador\s+se\s+obliga|TERCERO|CUARTO|SEXTO|S[EÉ]PTIMO|CL[AÁ]USULA|ESTADO\s+DE\s+PAGO)',
        r'en\s+las\s+siguientes\s+funciones\s*:\s*(.*?)(?:ESTADO\s+DE\s+PAGO|TERCERO|CUARTO|Modalidad)',
        r'Cometidos\s+espec[íi]ficos\s*:\s*(.*?)(?:TERCERO|CUARTO|ESTADO\s+DE\s+PAGO|Modalidad)',
        r'funciones\s*:\s*(.*?)(?:TERCERO|CUARTO|ESTADO\s+DE\s+PAGO|Modalidad)',
    ], flags=re.DOTALL | re.IGNORECASE)

    if match_sec:
        block = match_sec.group(1)

        numbered = re.findall(
            r'(?:^|\n)\s*\d+[\.\)]\s+(.+?)(?=\n\s*\d+[\.\)]|\s*$)',
            block, re.MULTILINE
        )
        if numbered:
            for m in numbered:
                clean = re.sub(r'\s+', ' ', m.strip())
                if clean and len(clean) > 5:
                    functions.append(clean)
        else:
            lines = block.split('\n')
            current_item = []
            for line in lines:
                stripped = line.strip()
                if re.match(r'^[-•*]\s*', stripped):
                    if current_item:
                        clean = re.sub(r'\s+', ' ', ' '.join(current_item).strip())
                        if clean and len(clean) > 5:
                            functions.append(clean)
                    current_item = [re.sub(r'^[-•*]\s*', '', stripped)]
                elif current_item and stripped:
                    current_item.append(stripped)
                elif not current_item and stripped and functions and len(stripped) > 15:
                    if not re.match(r'^(?:ESTADO|TERCERO|CUARTO|Modalidad|La Municipalidad|MUNICIPALIDAD)', stripped, re.IGNORECASE):
                        functions.append(stripped)

            if current_item:
                clean = re.sub(r'\s+', ' ', ' '.join(current_item).strip())
                if clean and len(clean) > 5:
                    functions.append(clean)

    if not functions:
        for line in text.split('\n'):
            line = line.strip()
            if any(k in line.lower() for k in ['función', 'cometido', 'deber', 'tarea']):
                m = re.match(r'^\s*(?:\d+[\.\)]\s*|[a-z][\.\)]\s*|[-•]\s*)(.+)$', line)
                if m:
                    clean = m.group(1).strip()
                    if clean and len(clean) > 10:
                        functions.append(clean)

    return functions