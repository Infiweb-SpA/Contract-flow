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

# 2. Desactivar oneDNN (enable_mkldnn=False)
ocr_engine = PaddleOCR(
    lang='es', 
    use_textline_orientation=False, 
    use_doc_orientation_classify=False, 
    use_doc_unwarping=False, 
    enable_mkldnn=False
)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Intenta extraer texto de un PDF de forma nativa. 
    Si no encuentra texto suficiente (probablemente un documento escaneado), 
    aplica OCR a las páginas convirtiéndolas a imagen primero.
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
    """Aplica PaddleOCR 3.x convirtiendo el PDF en imágenes con PyMuPDF."""
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
            print(f"    - Procesando página {page_index + 1}/{total_pages}...")
            try:
                # Reducimos el zoom a 1.5 (~108 DPI) para que sea más rápido en CPU
                page = doc.load_page(page_index)
                zoom = 1.5  
                #oom = 1.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convertir a array NumPy
                img_data = pix.tobytes("png")
                pil_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                #il_img = Image.open(io.BytesIO(img_data)).convert("L")
                img_array = np.array(pil_img)

                # Ejecutar predicción
                result_gen = ocr_engine.predict(input=img_array)

                # PaddleOCR 3.x a veces devuelve un generador, lo convertimos a lista
                if not isinstance(result_gen, list):
                    results = list(result_gen)
                else:
                    results = result_gen

                if results and len(results) > 0:
                    page_res = results[0]
                    
                    # Extraer los textos reconocidos
                    texts = []
                    if hasattr(page_res, 'rec_texts'):
                        texts = page_res.rec_texts
                    elif isinstance(page_res, dict) and 'rec_texts' in page_res:
                        texts = page_res['rec_texts']
                    
                    lines_count = 0
                    for t in texts:
                        if t and t.strip():
                            ocr_text += t.strip() + " "
                            lines_count += 1
                    ocr_text += "\n"
                    print(f"      ✓ Texto extraído en página {page_index + 1}: {lines_count} líneas")
                    
            except Exception as page_err:
                logging.error(f"Error OCR en página {page_index}: {page_err}")
                continue
        print("--> OCR finalizado.")
    finally:
        doc.close()

    return ocr_text.strip()
# =============================================================================
# AQUÍ MANTIENES TODO TU CÓDIGO ORIGINAL (Fechas y Parser)
# =============================================================================


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
    Analiza texto extraído de un contrato a honorarios municipal y extrae datos estructurados.
    Retorna un diccionario mapeado para auto-completar el formulario/contexto.
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
    # ── 1. NÚMERO DE CONTRATO Y DECRETO ──────────────────────────────────────
    match_ct = re.search(r'(?:N[°o]|N°\s*)(CT-\d{4}-\d{4})', full_text, re.IGNORECASE)
    if match_ct:
        data['contract_number'] = match_ct.group(1).upper()

    match_dec = re.search(r'Decreto\s+Alcaldicio\s+N[°o]?\s*(\d+)(?:\s+de\s+fecha\s+([\d\-]{10}))?', full_text, re.IGNORECASE)
    if match_dec:
        data['decline_number'] = match_dec.group(1)
        if match_dec.group(2):
            data['decline_date'] = match_dec.group(2)

    # ── 2. PRESTADOR DE SERVICIOS ────────────────────────────────────────────
    # Extrae directamente a don(ña) <nombre>, RUT <rut>, <profesion>
    match_prestador = re.search(
        r'don\(ña\)\s+([^\,]+),\s*cédula\s+de\s+identidad\s+N[°o]?\s*([\d\.\-kK]+)',
        full_text,
        re.IGNORECASE
    )
    if match_prestador:
        data['full_name'] = match_prestador.group(1).strip().title()
        data['rut'] = match_prestador.group(2).replace('.', '').strip().upper()

    # ── 3. CARGO, PROGRAMA, SUBPROGRAMA Y DEPARTAMENTO ───────────────────────
    match_prog = re.search(
        r'servicio\s+de\s+([^,]+),\s*para\s+el\s+programa\s+municipal\s+([^,]+)(?:,\s*subprograma\s+([^,]+))?,\s*dependiente\s+de\s+la\s+([^\.]+)',
        full_text,
        re.IGNORECASE
    )
    if match_prog:
        data['position_title'] = match_prog.group(1).strip().capitalize()
        data['program_name'] = match_prog.group(2).strip()
        if match_prog.group(3):
            data['sub_program'] = match_prog.group(3).strip()
        data['department_name'] = match_prog.group(4).strip()

    # ── 4. PRESUPUESTO ───────────────────────────────────────────────────────
    match_cuenta = re.search(r'cuenta\s+presupuestaria\s+N[°o]?\s*([\d\.]+)', full_text, re.IGNORECASE)
    if match_cuenta:
        data['budget_account'] = match_cuenta.group(1).strip()

    match_centro = re.search(r'centro\s+de\s+costo\s+([\d\.]+)', full_text, re.IGNORECASE)
    if match_centro:
        data['cost_center'] = match_centro.group(1).strip()

    # ── 5. FECHAS ────────────────────────────────────────────────────────────
    # Fecha de Firma
    match_firma = re.search(r'Fecha\s+de\s+firma:\s*([\d\-]{10})', full_text, re.IGNORECASE)
    if match_firma:
        data['contract_date'] = match_firma.group(1)

    # Fechas de Vigencia (Inicio y Término)
    match_vigencia = re.search(
        r'duración\s+desde\s+el\s+([\d\-]{10})\s+hasta\s+el\s+([\d\-]{10})',
        full_text,
        re.IGNORECASE
    )
    if match_vigencia:
        data['start_date'] = match_vigencia.group(1)
        data['end_date'] = match_vigencia.group(2)

    # ── 6. MONTOS (Sin errores de decimales flotantes) ──────────────────────
    match_monto = re.search(r'renta\s+bruta\s+mensual[^\$]*\$\s*([\d\.]+)', full_text, re.IGNORECASE)
    if match_monto:
        # Remueve el .0 al final en caso de venir del PDF
        raw_val = match_monto.group(1).split('.')[0]
        try:
            data['monthly_amount_gross'] = int(raw_val)
        except ValueError:
            pass

    match_total = re.search(r'monto\s+total\s+del\s+contrato[^\$]*\$\s*([\d\.]+)', full_text, re.IGNORECASE)
    if match_total:
        raw_total = match_total.group(1).split('.')[0]
        try:
            data['total_contract_amount'] = int(raw_total)
        except ValueError:
            pass

    if 'producto o servicio entregado' in full_text.lower():
        data['payment_modality'] = 'POR_PRODUCTO'

    # ── 7. FUNCIONES ESPECÍFICAS (Aisladas de la Cláusula Quinta) ─────────────
    data['functions'] = extract_functions(full_text)

    return data


def _parse_date_string(date_str: str) -> str:
    """Helper interno para convertir cualquier variante de fecha a ISO YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # Si ya es ISO (2026-06-19)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Formato text "19 de junio de 2026"
    match_text = re.search(r'(\d{1,2})\s+de\s+([a-zA-Z]+)\s+de\s+(\d{4})', date_str, re.IGNORECASE)
    if match_text:
        day, month_name, year = match_text.groups()
        month = _MONTHS_ES.get(month_name.lower(), 1)
        return f"{int(year):04d}-{month:02d}-{int(day):02d}"

    # Formato DD/MM/YYYY
    match_slash = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if match_slash:
        day, month, year = match_slash.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    return date_str


def extract_functions(text: str) -> list:
    functions = []
    # Busca únicamente el bloque numerado entre "siguientes:" y "El Prestador se obliga"
    match_sec = re.search(
        r'Serán\s+funciones\s+específicas\s+del\s+Prestador\s+las\s+siguientes:\s*(.*?)(?=El\s+Prestador\s+se\s+obliga|SEXTO:|$)',
        text,
        re.DOTALL | re.IGNORECASE
    )
    if match_sec:
        block = match_sec.group(1)
        # Extrae las líneas numeradas tipo 1. 2. 3.
        matches = re.findall(r'^\s*\d+[\.\)]\s*(.+)$', block, re.MULTILINE)
        for m in matches:
            clean = m.strip()
            if clean:
                functions.append(clean)
    return functions