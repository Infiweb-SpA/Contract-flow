import os
# Configuración compatible con PaddleOCR/PaddlePaddle en Railway (CPU).
# Desactivamos PIR y oneDNN para evitar errores de compatibilidad del runtime.
os.environ['FLAGS_enable_pir_in_executor'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

# Evita que PaddleX se quede comprobando los servidores de modelos al iniciar.
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# Limitar hilos evita saturar el CPU de Railway durante la inferencia.
os.environ['OMP_NUM_THREADS'] = '2'
os.environ['MKL_NUM_THREADS'] = '2'

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


# Desactivar oneDNN/MKLDNN.
# En Railway esto evita el error:
# ConvertPirAttribute2RuntimeAttribute not support
# [pir::ArrayAttribute<pir::DoubleAttribute>]
ocr_engine = PaddleOCR(
    lang='es',
    # Modelos mobile: mucho más apropiados para CPU/Railway
    # que los modelos medium/server que estaban cargándose.
    text_detection_model_name='PP-OCRv5_mobile_det',
    text_recognition_model_name='PP-OCRv5_mobile_rec',

    use_textline_orientation=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,

    # Desactivado para evitar el error PIR/oneDNN observado en Railway.
    enable_mkldnn=False,

    # Railway normalmente dispone de CPU limitada.
    cpu_threads=2,
    device='cpu',
)


def extract_text_from_pdf(file_path: str, is_cancelled=None, on_progress=None) -> str:
    """
    Intenta extraer texto de un PDF de forma nativa.
    Si no encuentra texto suficiente (probablemente un documento escaneado),
    aplica OCR a las páginas convirtiéndolas a imagen primero.

    Args:
        file_path: Ruta al archivo PDF.
        is_cancelled: Callable opcional que retorna True si el procesamiento
                      debe ser cancelado. Se verifica entre cada página del OCR.
        on_progress: Callable opcional que recibe un diccionario con el
                     progreso real: {'progress': int 0-100, 'phase': str,
                     'total_pages': int, 'current_page': int}.
    """
    extracted_text = ""
    needs_ocr = False

    def report(progress, phase, total_pages=0, current_page=0):
        if on_progress:
            try:
                on_progress({
                    'progress': progress,
                    'phase': phase,
                    'total_pages': total_pages,
                    'current_page': current_page,
                })
            except Exception:
                pass

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            report(5, 'reading', total_pages, 0)
            for idx, page in enumerate(pdf.pages):
                if is_cancelled and is_cancelled():
                    raise OCRCancelledException("Procesamiento cancelado durante la lectura")
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
                # Progreso real de lectura: 5% → 45%
                report(5 + int(40 * (idx + 1) / max(total_pages, 1)),
                       'reading', total_pages, idx + 1)

            # Si el texto extraído es muy corto, asumimos que es una imagen escaneada
            if len(extracted_text.strip()) < 50:
                needs_ocr = True

        if needs_ocr:
            extracted_text = _extract_via_ocr(file_path, is_cancelled=is_cancelled,
                                               on_progress=on_progress)
        else:
            report(95, 'parsing')

        return extracted_text.strip()

    except OCRCancelledException:
        raise
    except Exception as e:
        logging.error(f"Error procesando PDF {file_path}: {str(e)}")
        raise e


def _extract_via_ocr(file_path: str, is_cancelled=None, on_progress=None) -> str:
    """
    Aplica PaddleOCR 3.x convirtiendo el PDF en imágenes con PyMuPDF.

    Args:
        file_path: Ruta al archivo PDF.
        is_cancelled: Callable opcional que se invoca entre cada página.
                      Si retorna True, se detiene el procesamiento inmediatamente.
        on_progress: Callable opcional que reporta el progreso real por página.
    """
    ocr_text = ""

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logging.error(f"No se pudo abrir el PDF con PyMuPDF {file_path}: {e}")
        return ""

    total_pages = len(doc)
    print(f"--> Iniciando OCR para {total_pages} páginas...", flush=True)

    if on_progress:
        try:
            on_progress({'progress': 45, 'phase': 'ocr', 'total_pages': total_pages,
                         'current_page': 0})
        except Exception:
            pass

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

            print(f"    - Procesando página {page_index + 1}/{total_pages}...", flush=True)
            try:
                page = doc.load_page(page_index)
                # 1.25 reduce bastante el costo de CPU/RAM sin degradar
                # demasiado la lectura de contratos escaneados.
                zoom = 1.25
                mat = fitz.Matrix(zoom, zoom)

                print(
                    f"      [OCR] Renderizando página {page_index + 1}...",
                    flush=True
                )
                pix = page.get_pixmap(matrix=mat, alpha=False)

                print(
                    f"      [OCR] Imagen: {pix.width}x{pix.height}",
                    flush=True
                )

                #img_data = pix.tobytes("png")
                #pil_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                #img_array = np.array(pil_img)
                #result_gen = ocr_engine.predict(input=img_array)
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

                print(
                    f"      [OCR] Ejecutando PaddleOCR en página {page_index + 1}...",
                    flush=True
                )

                result_gen = ocr_engine.predict(input=img_array)

                print(
                    f"      [OCR] PaddleOCR terminó página {page_index + 1}.",
                    flush=True
                )

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
                    print(
                        f"      ✓ Texto extraído en página {page_index + 1}: {lines_count} líneas",
                        flush=True
                    )

            except OCRCancelledException:
                raise
            except Exception as page_err:
                logging.exception(
                    f"Error OCR en página {page_index + 1}: {page_err}"
                )
                continue

            # ── Reportar progreso real de la página procesada ──
            if on_progress:
                try:
                    pct = 45 + int(50 * (page_index + 1) / max(total_pages, 1))
                    on_progress({
                        'progress': min(pct, 95),
                        'phase': 'ocr',
                        'total_pages': total_pages,
                        'current_page': page_index + 1,
                    })
                except Exception:
                    pass

        print("--> OCR finalizado.", flush=True)
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

    # DD de mes de YYYY (ej: "30 de junio de 2026", "01 de julio del 2025")
    m = re.search(r'(\d{1,2})\s+de\s+([a-zA-Záéíóú]+)\s+del?\s+(\d{4})', date_str, re.IGNORECASE)
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
        'provider_comuna': None,
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
        'hours_weekly': None,

        # Fechas y Documentos
        'start_date': None,
        'end_date': None,
        'contract_date': None,
        'decline_number': None,
        'decline_date': None,
        'contract_number': None,

        # Funciones
        'functions': [],
        'decrees': [],
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

    # ── 4b. DOMICILIO, COMUNA Y JORNADA (estructura Cunco) ─────────────────
    match_dom = _try_match(full_text, [
        r'domiciliad[oa]\s*(?:\(a\))?s?\s+en\s+([A-ZÁÉÍÓÚÑa-z][^,.;]{0,80}?),\s*(?:de\s+la\s+)?comuna\s+(?:de\s+la\s+)?([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{0,25}?)(?:,|\s+en\s+adelante|\.)',
        r'con\s+domicilio\s+en\s+([A-ZÁÉÍÓÚÑa-z][^,.;]{0,80}?),\s*(?:de\s+la\s+)?comuna\s+(?:de\s+la\s+)?([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]{0,25}?)(?:,|\s+en\s+adelante|\.)',
        r'domiciliad[oa]\s*(?:\(a\))?s?\s+en\s+([A-ZÁÉÍÓÚÑa-z][^,.;]{0,60}),',
    ])
    if match_dom:
        data['provider_address'] = match_dom.group(1).strip()
        if match_dom.lastindex and match_dom.lastindex >= 2:
            data['provider_comuna'] = match_dom.group(2).strip()

    # Jornada horaria: 'con una jornada de 44 horas semanales'
    match_hours = re.search(r'jornada\s+(?:de\s+|flexible\s+de\s+)?(\d{1,2})\s+horas?', full_text, re.IGNORECASE)
    if match_hours:
        hours = int(match_hours.group(1))
        if 0 < hours <= 60:
            data['hours_weekly'] = hours

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

    # ── 12. VISTOS / DECRETOS PREVIOS ─────────────────────────────────────
    data['decrees'] = extract_decrees_vistos(full_text)

    # ── 13. FUNCIONES ─────────────────────────────────────────────────────
    data['functions'] = extract_functions(full_text)

    # ── DEBUG: Log de campos extraídos ─────────────────────────────────────
    extracted_fields = {k: v for k, v in data.items() if v is not None and k not in ('raw_text', 'functions', 'decrees')}
    logging.info(f"OCR Parser: {len(extracted_fields)} campos extraídos: {list(extracted_fields.keys())}")
    if data['functions']:
        logging.info(f"OCR Parser: {len(data['functions'])} funciones extraídas")
    if data['decrees']:
        logging.info(f"OCR Parser: {len(data['decrees'])} decretos/VISTOS extraídos")

    return data


def _parse_date_string(date_str: str) -> str:
    """Helper interno para convertir cualquier variante de fecha a ISO YYYY-MM-DD."""
    return _parse_any_date(date_str)


# =============================================================================
# PARSER DEL BLOQUE "VISTOS" (DECRETOS Y ANTECEDENTES PREVIOS)
# =============================================================================

# Sellos/timbres que el scanner superpone sobre el documento: aparecen como
# líneas sueltas dentro del bloque VISTOS y NO son ítems. Cada alternativa
# debe cubrir la línea COMPLETA (anclada a fin de línea) para no tumbar
# fragmentos legítimos de los VISTOS. CASE-SENSITIVE: los sellos reales van
# en MAYÚSCULAS; las continuaciones reales suelen traer minúsculas.
_DECREE_STAMP_RE = re.compile(
    r'^\s*(?:'
    r'[a-zA-Z]{1,4}\s*$|'                                  # ruido: 'ef', 'nc', 'O'
    r'(?:FECHA|HORA|TELÉFONO|MAIL)\b.*$|'                  # sellos: 'FECHA SALIDA', 'HORA'
    r'POR\s*$|NC\s*$|_DE\s*$|_POR\s*$|'                    # fragmentos de sello
    r'\d{1,2}[A-Z]{3}\.?\s*\d{2,4}\s*$|'                   # '15JUL.2025', '21JUL.2026'
    r'\d{1,2}\.\d{2}\s*$|'                                 # '13.40'
    r'REPRESENTACION\b.*$|'                                # sello 'REPRESENTACION NC'
    r'DIRECTOR\s+DE\s+CONTROL.*$|'
    r'(?:Was|M[aá]s)\s+cerc[aá][^ü]*$|'                    # timbre 'Está/Was cerca de usted'
    r'Wnc\s*$|'
    r'[A-ZÁÉÍÓÚÑ(]{2,}[\.\s]*$|'                           # siglas puras: 'CUNCO'
    r'[A-ZÁÉÍÓÚÑ](?:[A-ZÁÉÍÓÚÑ/\s\-]{0,40}[A-ZÁÉÍÓÚÑ.])\s*$'  # frases cortas en mayúsculas
    r')'
)

# Inicio de ítem numerado: número de 1-2 dígitos seguido POR UN DELIMITADOR
# (punto, paréntesis, guion, º°:) y el resto del texto. El delimitador es
# obligatorio: evita tratar fechas como '06 de diciembre...' como numeración.
_DECREE_ITEM_START_RE = re.compile(r'^(\d{1,2})\s*[\.º°\)\:\-]\s*(.*)')


def _normalize_ocr_word_fixes(text: str) -> str:
    """Corrige confusiones típicas del OCR en español: EI→El, Ia→la, Req→reg."""
    text = re.sub(r'\bEI\b', 'El', text)
    text = re.sub(r'\beI\b', 'el', text)
    text = re.sub(r'\bIa\b', 'la', text)
    text = re.sub(r'Req([a-záéíóúñ])', r'reg\1', text)
    text = re.sub(r'municipaI', 'municipal', text)
    text = re.sub(r'estad?s?\s+de\s+pago', 'estados de pago', text, flags=re.IGNORECASE)
    # Fechas partidas por espacios: '11 /12/2025' → '11/12/2025'
    text = re.sub(r'(\d{1,2})\s+/\s*(\d{1,2})\s*/\s*(\d{2,4})', r'\1/\2/\3', text)
    return text


def _classify_decree(desc: str) -> str:
    """Clasifica un decreto/VISTO por su contenido. Retorna un código de tipo."""
    d = desc.lower()

    if re.search(r'ficha\s+de\s+ingreso', d, re.IGNORECASE):
        return 'FICHA_RRHH'
    if 'anterior' in d and re.search(r'contrat', d, re.IGNORECASE):
        return 'CONTRATO_ANTERIOR'
    # El propio contrato del expediente (sin la palabra 'anterior')
    if re.search(r'(?:el\s+)?contrat[oa]\s+a?\s+prestaci[óo]n\s+de\s+servicios', d, re.IGNORECASE):
        return 'CONTRATO_ACTUAL'
    if re.search(r'subrogaci[óo]n', d, re.IGNORECASE):
        if re.search(r'control', d, re.IGNORECASE):
            return 'SUBROGANCIA_CONTROL'
        if re.search(r'alcalde', d, re.IGNORECASE):
            return 'SUBROGANCIA_ALCALDE'
        return 'SUBROGANCIA_CONTROL'
    if re.search(r'plan\s+operativo\s+anual?|\bPOA\b', d, re.IGNORECASE):
        return 'PROGRAMA_MUNICIPAL'
    if re.search(r'programa', d, re.IGNORECASE):
        return 'PROGRAMA_MUNICIPAL'
    if re.search(r'presupuesto|desagregaci[óo]n|desgloses?|subt[íi]tulos', d, re.IGNORECASE):
        return 'PRESUPUESTO_ANUAL'
    if re.search(r'resoluci[óo]n|contralor[íi]a|oficio|ley\s+n?[°oº\.]*\s*\d|ley\s+\d|facultades', d, re.IGNORECASE):
        return 'BASE_LEGAL'
    if re.search(r'fallo|calificaci[óo]n|concejo|municipal|asume\s+el\s+cargo|nombra\s+', d, re.IGNORECASE):
        return 'ANTECEDENTE_INSTITUCIONAL'
    if re.search(r'decreto', d, re.IGNORECASE):
        return 'ANTECEDENTE_INSTITUCIONAL'
    return 'OTRO'


def _extract_decree_ref(desc: str):
    """
    Busca dentro del texto del VISTO el número y la fecha del documento
    referenciado (ej: 'Decreto Exento N° 3.074 de fecha 17.12.2024').
    Retorna (decree_number, decree_date_iso).
    """
    number = None
    m = re.search(
        r'(?:Decreto\s+(?:Exento|Alcaldicio)|Resoluci[óo]n|Oficio|Ley)\s+N[°oº\.]*\s*([\d\.\-]+)',
        desc, re.IGNORECASE
    )
    if m:
        number = m.group(1).strip('.- ')

    date_iso = None
    date_patterns = [
        r'del?\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'de\s+fecha\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'de\s+fecha\s+(\d{1,2}\s+de\s+[a-záéíóú]+\s+del?\s+\d{4})',
        r'del\s+(\d{1,2}\s+de\s+[a-záéíóú]+\s+(?:del\s+)?(?:a[ñn]o\s+)?\d{4})',
        r'de\s+(\d{1,2}\s+de\s+[a-záéíóú]+\s+del?\s+\d{4})',
        r'(\d{1,2}\s+de\s+[a-záéíóú]+\s+del?\s+\d{4})',
        r'fecha\s+([\d\-/]{8,12})',
    ]
    for pat in date_patterns:
        dm = re.search(pat, desc, re.IGNORECASE)
        if dm:
            date_iso = _parse_any_date(dm.group(1))
            break

    return number, date_iso


def extract_decrees_vistos(text: str) -> list:
    """
    Extrae el bloque VISTOS: decretos y antecedentes previos del contrato.
    Detecta la cabecera 'VISTOS:' y procesa la lista numerada que sigue
    (ítems multilínea), descartando sellos/timbres del escaneo.

    Retorna una lista de dicts con claves:
        {'decree_type', 'decree_number', 'decree_date', 'description'}
    listos para instanciar ContractDecree (origin MANUAL).
    """
    decrees = []
    if not text:
        return decrees

    # ── Localizar el bloque VISTOS (del marcador hasta 'DECRETO:' / 'ANOTÉSE') ──
    match_block = re.search(
        r'VISTOS\s*:?([\s\S]{0,10000}?)(?=\n\s*DECRETO\s*:|\n\s*ANOT[EÉ]SE|\n\s*RESUELVE|\n\s*CONSIDERANDO\s+QUE)',
        text, re.IGNORECASE
    )
    if not match_block:
        return decrees

    block = match_block.group(1)
    lines = block.split('\n')

    items = []       # textos ya unidos, uno por ítem numerado
    current = None   # lista de líneas del ítem en formación
    last_num = 0     # último número de ítem aceptado (guardia contra sellos)

    for line in lines:
        stripped = re.sub(r'\s+', ' ', line.strip())
        if not stripped:
            continue

        mnum = _DECREE_ITEM_START_RE.match(stripped)
        is_new_item = False
        if mnum:
            try:
                n = int(mnum.group(1))
                rest = (mnum.group(2) or '').strip()
                # '13.40' y similares: décimales del sello, no numeración.
                if rest.isdigit() and len(rest) <= 2:
                    is_new_item = False
                # Numeración aceptada si es estrictamente creciente (~1,2,3...),
                # arranca el bloque, o salta de secuencia con texto largo (OCR
                # que garbleó el ítem anterior, ej: 'g°' en vez de '9.').
                elif n == last_num + 1 or (last_num == 0 and n <= 3) or (n > last_num and len(rest) > 40):
                    is_new_item = True
            except ValueError:
                pass

        if is_new_item:
            if current:
                joined = ' '.join(current).strip()
                if joined:
                    items.append(joined)
            current = [stripped]
            last_num = int(mnum.group(1))
        elif current is not None:
            # Línea de continuación: filtra sellos del scanner
            if len(stripped) <= 45 and _DECREE_STAMP_RE.match(stripped):
                continue
            current.append(stripped)
        # Líneas previas al primer ítem (cabecera del decreto): se ignoran.

    if current:
        joined = ' '.join(current).strip()
        if joined:
            items.append(joined)

    # ── El bloque VISTOS queda rodeado de timbres del pie/cabecera de página ──
    # Recorta, del ÚLTIMO ítem, la cola de membrete institucional detrás del
    # texto real (mayúsculas del membrete, nunca texto de los VISTOS).
    if items:
        _noise_tail_re = re.compile(
            r'CUNCO\s*MUNICIPALIDAD|MUNICIPALIDAD\s+DE\s+[A-ZÁÉÍÓÚÑ]+\s+DIRECCI|'
            r'DIRECCI[ÓO]N\s+DE\s+[A-ZÁÉÍÓÚÑ]+|UNIDAD\s+(?:DE\s+)?RECURSOS|'
            r'REPRESENTACION|DIRECTOR\s+DE\s+CONTROL|DECRETO\s+ALCALDICIO'
        )
        last_text = items[-1]
        m_noise = _noise_tail_re.search(last_text)
        if m_noise and m_noise.start() > 0:
            items[-1] = last_text[:m_noise.start()].rstrip(' .,;')

    # ── Armar los decretos con su metadato tipo/número/fecha ──
    for raw in items:
        description = re.sub(r'\s+', ' ', _normalize_ocr_word_fixes(raw)).strip()
        # Quitar la numeración inicial OCR ('1. ', '12) ', '10- ')
        description = re.sub(r'^\d{1,2}\s*[\.\)\-º°:]\s*', '', description).strip()

        if not description or len(description) < 15:
            continue

        decree_number, decree_date = _extract_decree_ref(description)

        decrees.append({
            'decree_type': _classify_decree(description),
            'decree_number': decree_number,
            'decree_date': decree_date,
            'description': description,
        })

    return decrees


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