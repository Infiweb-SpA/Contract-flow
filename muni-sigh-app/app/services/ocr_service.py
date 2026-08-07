import os
import pdfplumber
from paddleocr import PaddleOCR
import logging

# Inicializar PaddleOCR (solo idioma español)
# Quitamos show_log=False para evitar el ValueError
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
    
    # PaddleOCR soporta lectura directa de PDFs a partir de ciertas versiones
    # extrayendo las imágenes internamente.
    result = ocr_engine.ocr(file_path, cls=True)
    
    # El resultado es una lista de páginas, cada página tiene cajas de texto
    for page_result in result:
        if page_result:
            for line in page_result:
                # line[1][0] contiene el texto reconocido
                ocr_text += line[1][0] + " "
            ocr_text += "\n"
            
    return ocr_text