import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.auth.utils import login_required
from app.models.contract import Contract
from app.services.ocr_service import extract_text_from_pdf

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

def allowed_file(filename):
    """Verifica que el archivo tenga una extensión permitida configurada en config.py"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@payments_bp.route('/contract/<int:contract_id>/validate', methods=['GET', 'POST'])
@login_required
def validate_report(contract_id):
    # Obtener el contrato y sus funciones vinculadas
    contract = Contract.query.get_or_404(contract_id)
    
    # Variables iniciales para la vista
    pdf_url = None
    extracted_text = ""
    
    if request.method == 'POST':
        # Validar que el request contenga un archivo
        if 'report_file' not in request.files:
            flash('No se adjuntó ningún archivo en la petición.', 'danger')
            return redirect(request.url)
            
        file = request.files['report_file']
        
        if file.filename == '':
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Asegurar el nombre del archivo y guardarlo
            filename = secure_filename(f"informe_ct_{contract.id}_{file.filename}")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Generar la URL pública para el iframe (apunta a static/uploads)
            pdf_url = url_for('static', filename=f'uploads/{filename}')
            
            try:
                # 🚀 Ejecutar el motor de extracción y OCR
                extracted_text = extract_text_from_pdf(filepath)
                flash('Archivo procesado exitosamente por el motor de extracción.', 'success')
            except Exception as e:
                flash(f'Error procesando el documento: {str(e)}', 'danger')
        else:
            flash('Formato de archivo no permitido. Solo se aceptan PDFs.', 'warning')
            
    return render_template(
        'payments/split_view.html', 
        contract=contract, 
        pdf_url=pdf_url, 
        extracted_text=extracted_text
    )