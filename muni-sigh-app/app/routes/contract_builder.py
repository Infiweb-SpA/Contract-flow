# app/routes/contract_builder.py
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.utils import secure_filename
from app import db
from app.auth.utils import login_required, role_required, get_current_user
from app.models.user import Department
from app.models.provider import ServiceProvider
from app.models.contract import Contract, ContractFunction
from app.services.audit_service import log_action
from app.services.pdf_generator import generate_contract_html, make_pdf_response
from app.services.ocr_service import extract_text_from_pdf
import os

contract_builder_bp = Blueprint('contract_builder', __name__, url_prefix='/contracts')


# =============================================================================
# CREAR CONTRATO
# =============================================================================
@contract_builder_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def create():
    if request.method == 'POST':
        try:
            provider_id = request.form.get('provider_id')
            department_id = request.form.get('department_id')
            contract_number = request.form.get('contract_number', '').strip()
            decline_number = request.form.get('decline_number', '').strip()
            decline_date_str = request.form.get('decline_date')
            position_title = request.form.get('position_title', '').strip()
            program_name = request.form.get('program_name', '').strip()
            monthly_amount_gross = float(request.form.get('monthly_amount_gross', 0))
            total_contract_amount = float(request.form.get('total_contract_amount', 0)) or monthly_amount_gross
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

            decline_date = datetime.strptime(decline_date_str, '%Y-%m-%d').date() if decline_date_str else None

            new_contract = Contract(
                provider_id=provider_id,
                department_id=department_id,
                creation_type='CREADO',
                contract_number=contract_number,
                decline_number=decline_number,
                decline_date=decline_date,
                position_title=position_title,
                program_name=program_name,
                monthly_amount_gross=monthly_amount_gross,
                total_contract_amount=total_contract_amount,
                start_date=start_date,
                end_date=end_date,
                status='BORRADOR'
            )
            db.session.add(new_contract)
            db.session.flush()

            functions = request.form.getlist('functions[]')
            for index, func_desc in enumerate(functions, start=1):
                clean_desc = func_desc.strip()
                if clean_desc:
                    func = ContractFunction(
                        contract_id=new_contract.id,
                        function_order=index,
                        function_description=clean_desc,
                        is_mandatory_for_payment=1
                    )
                    db.session.add(func)

            db.session.commit()

            log_action(
                action='CONTRACT_CREATE',
                entity_type='contract',
                entity_id=new_contract.id,
                payload={'contract_number': contract_number, 'provider_id': provider_id}
            )

            flash(f'Contrato N° {contract_number} creado exitosamente.', 'success')
            return redirect(url_for('contract_builder.detail', contract_id=new_contract.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al armar el contrato: {str(e)}', 'danger')

    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()

    return render_template('contracts/create.html', providers=providers, departments=departments)


# =============================================================================
# DETALLE DEL CONTRATO
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>')
@login_required
def detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    return render_template('contracts/detail.html', contract=contract)


# =============================================================================
# EDITAR CONTRATO
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def edit(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    
    if request.method == 'POST':
        try:
            contract.contract_number = request.form.get('contract_number', '').strip()
            contract.decline_number = request.form.get('decline_number', '').strip()
            decline_date_str = request.form.get('decline_date')
            contract.decline_date = datetime.strptime(decline_date_str, '%Y-%m-%d').date() if decline_date_str else None
            contract.position_title = request.form.get('position_title', '').strip()
            contract.program_name = request.form.get('program_name', '').strip()
            contract.monthly_amount_gross = float(request.form.get('monthly_amount_gross', 0))
            contract.total_contract_amount = float(request.form.get('total_contract_amount', 0))
            contract.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            contract.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            contract.status = request.form.get('status', 'BORRADOR')
            
            ContractFunction.query.filter_by(contract_id=contract.id).delete()
            functions = request.form.getlist('functions[]')
            for index, func_desc in enumerate(functions, start=1):
                clean_desc = func_desc.strip()
                if clean_desc:
                    db.session.add(ContractFunction(
                        contract_id=contract.id,
                        function_order=index,
                        function_description=clean_desc,
                        is_mandatory_for_payment=1
                    ))
            
            db.session.commit()
            log_action('CONTRACT_UPDATE', 'contract', contract.id, {'contract_number': contract.contract_number})
            flash('Contrato actualizado exitosamente.', 'success')
            return redirect(url_for('contract_builder.detail', contract_id=contract.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')
    
    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()
    return render_template('contracts/edit.html', contract=contract, providers=providers, departments=departments)


# =============================================================================
# VISTA PREVIA / BORRADOR
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>/preview')
@login_required
def preview(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    return generate_contract_html(contract)


# =============================================================================
# DESCARGAR PDF
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>/download-pdf')
@login_required
def download_pdf(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    try:
        return make_pdf_response(contract)
    except Exception as e:
        flash(f'Error generando PDF: {str(e)}. Use la vista de impresión del navegador.', 'danger')
        return redirect(url_for('contract_builder.preview', contract_id=contract.id))


# =============================================================================
# CAMBIAR ESTADO
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>/change-status', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN')
def change_status(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    new_status = request.form.get('new_status')
    
    valid_transitions = {
        'BORRADOR': ['CREADO_PARA_FIRMA'],
        'CREADO_PARA_FIRMA': ['INGRESADO'],
        'INGRESADO': ['EN_EJECUCION'],
        'EN_EJECUCION': ['FINALIZADO']
    }
    
    current = contract.status
    allowed = valid_transitions.get(current, [])
    
    if new_status in allowed:
        contract.status = new_status
        db.session.commit()
        log_action('CONTRACT_STATUS_CHANGE', 'contract', contract.id, 
                   {'from': current, 'to': new_status})
        flash(f'Estado actualizado a: {contract.status_label}', 'success')
    else:
        flash(f'Transición no permitida: {current} → {new_status}', 'danger')
    
    return redirect(url_for('contract_builder.detail', contract_id=contract.id))


# =============================================================================
# CARGAR CONTRATO EXTERNO (OCR)
# =============================================================================
@contract_builder_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN')
def upload_external():
    if request.method == 'POST':
        try:
            provider_id = request.form.get('provider_id')
            department_id = request.form.get('department_id')
            contract_number = request.form.get('contract_number', '').strip()
            position_title = request.form.get('position_title', '').strip()
            monthly_amount_gross = float(request.form.get('monthly_amount_gross', 0))
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

            if 'contract_pdf' not in request.files:
                flash('Debe adjuntar el PDF del contrato.', 'danger')
                return redirect(request.url)

            file = request.files['contract_pdf']
            if file.filename == '':
                flash('No se seleccionó ningún archivo.', 'danger')
                return redirect(request.url)

            if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'pdf':
                filename = secure_filename(f"ext_{contract_number}_{file.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                extracted_text = ""
                try:
                    extracted_text = extract_text_from_pdf(filepath)
                except Exception as ocr_e:
                    flash(f'Advertencia OCR: {str(ocr_e)}', 'warning')

                new_contract = Contract(
                    provider_id=provider_id,
                    department_id=department_id,
                    creation_type='CARGADO_EXTERNO',
                    contract_number=contract_number,
                    position_title=position_title,
                    monthly_amount_gross=monthly_amount_gross,
                    total_contract_amount=monthly_amount_gross,
                    start_date=start_date,
                    end_date=end_date,
                    pdf_file_path=filepath,
                    ocr_processed=1 if extracted_text else 0,
                    status='INGRESADO'
                )
                db.session.add(new_contract)
                db.session.flush()

                if extracted_text:
                    lines = [l.strip() for l in extracted_text.split('\n') if len(l.strip()) > 10]
                    for idx, line in enumerate(lines[:15], start=1):
                        if any(k in line.lower() for k in ['función', 'cometido', 'deber', 'tarea', 'prestador', 'servicio']):
                            db.session.add(ContractFunction(
                                contract_id=new_contract.id,
                                function_order=idx,
                                function_description=line,
                                is_mandatory_for_payment=1
                            ))

                db.session.commit()
                log_action('CONTRACT_UPLOAD', 'contract', new_contract.id, 
                           {'contract_number': contract_number, 'ocr': bool(extracted_text)})
                flash(f'Contrato externo N° {contract_number} cargado. Revise las funciones extraídas.', 'success')
                return redirect(url_for('contract_builder.edit', contract_id=new_contract.id))
            else:
                flash('Solo se permiten archivos PDF.', 'warning')

        except Exception as e:
            db.session.rollback()
            flash(f'Error al cargar contrato externo: {str(e)}', 'danger')

    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()
    return render_template('contracts/upload.html', providers=providers, departments=departments)


# =============================================================================
# APIs
# =============================================================================
@contract_builder_bp.route('/api/search-provider', methods=['GET'])
@login_required
def search_provider():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'providers': []})
    
    providers = ServiceProvider.query.filter(
        db.or_(
            ServiceProvider.rut.ilike(f'%{query}%'),
            ServiceProvider.first_name.ilike(f'%{query}%'),
            ServiceProvider.paternal_last_name.ilike(f'%{query}%'),
            ServiceProvider.maternal_last_name.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = []
    for p in providers:
        results.append({
            'id': p.id,
            'rut': p.rut,
            'full_name': p.full_name,
            'email': p.email or '',
            'phone': p.phone or '',
            'address': p.address or ''
        })
        
    return jsonify({'success': True, 'providers': results})


@contract_builder_bp.route('/provider/quick-add', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN')
def quick_add_provider():
    try:
        data = request.get_json()
        rut = data.get('rut', '').strip()

        existing = ServiceProvider.query.filter_by(rut=rut).first()
        if existing:
            return jsonify({'success': False, 'message': 'El RUT ingresado ya se encuentra registrado.'}), 400

        new_provider = ServiceProvider(
            rut=rut,
            first_name=data.get('first_name', '').strip(),
            paternal_last_name=data.get('paternal_last_name', '').strip(),
            maternal_last_name=data.get('maternal_last_name', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            address=data.get('address', '').strip(),
            bank_name=data.get('bank_name', '').strip(),
            account_type=data.get('account_type', '').strip(),
            account_number=data.get('account_number', '').strip()
        )
        db.session.add(new_provider)
        db.session.commit()

        log_action('PROVIDER_CREATE', 'service_provider', new_provider.id, {'rut': rut})

        return jsonify({
            'success': True,
            'id': new_provider.id,
            'name': f"{new_provider.full_name} ({new_provider.rut})"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@contract_builder_bp.route('/department/quick-add', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN')
def quick_add_department():
    """Crea un departamento rápidamente desde el armador de contratos."""
    try:
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        cost_center = data.get('cost_center', '').strip()

        if not code or not name:
            return jsonify({'success': False, 'message': 'Código y nombre son obligatorios.'}), 400

        existing = Department.query.filter(
            db.or_(Department.code == code, Department.name == name)
        ).first()
        if existing:
            return jsonify({'success': False, 'message': 'Ya existe un departamento con ese código o nombre.'}), 400

        new_dept = Department(
            code=code,
            name=name,
            cost_center=cost_center or None,
            is_active=1
        )
        db.session.add(new_dept)
        db.session.commit()

        log_action('DEPARTMENT_CREATE', 'department', new_dept.id, {'code': code, 'name': name})

        return jsonify({
            'success': True,
            'id': new_dept.id,
            'label': f"{new_dept.code} - {new_dept.name}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500