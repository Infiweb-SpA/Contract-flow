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
from app.services.pdf_generator import generate_contract_html, make_pdf_response, generate_contract_preview
from app.services.ocr_service import extract_text_from_pdf, parse_contract_data, format_date_es
import os
import tempfile
import uuid

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
# VISTA PREVIA / BORRADOR (para contratos ya guardados)
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
# CARGAR CONTRATO EXTERNO (OCR) — Flujo clásico
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
# API: PREVISUALIZACIÓN EN VIVO (Split-View)
# =============================================================================
@contract_builder_bp.route('/api/preview', methods=['POST'])
@login_required
def api_preview():
    """
    Recibe los datos actuales del formulario vía JSON y devuelve el HTML
    renderizado del contrato para mostrarlo en el iframe de previsualización.
    No guarda nada en la base de datos.
    """
    try:
        data = request.get_json() or {}

        # Buscar nombres reales si tenemos IDs
        provider_name = data.get('provider_name', '____________________')
        provider_rut = data.get('provider_rut', '____________________')
        department_name = data.get('department_name', '____________________')

        if data.get('provider_id'):
            provider = ServiceProvider.query.get(data['provider_id'])
            if provider:
                provider_name = provider.full_name
                provider_rut = provider.rut

        if data.get('department_id'):
            dept = Department.query.get(data['department_id'])
            if dept:
                department_name = dept.name

        # Formatear fechas en español (sin depender del locale del sistema)
        start_date_str = format_date_es(data.get('start_date'))
        end_date_str = format_date_es(data.get('end_date'))
        decline_date_str = format_date_es(data.get('decline_date'))

        # Formatear monto
        monto = data.get('monthly_amount_gross')
        monto_str = "{:,.0f}".format(float(monto)) if monto else '__________'

        # Construir objeto de preview
        preview_data = {
            'contract_number': data.get('contract_number', 'CT-XXXX-XXX') or 'CT-XXXX-XXX',
            'position_title': data.get('position_title', '____________________'),
            'program_name': data.get('program_name', 'Gestión Municipal'),
            'monthly_amount_gross': monto_str,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'decline_number': data.get('decline_number', ''),
            'decline_date': decline_date_str,
            'created_at': datetime.now(),
            'provider_name': provider_name,
            'provider_rut': provider_rut,
            'department_name': department_name,
            'functions': [f.strip() for f in data.get('functions', []) if f.strip()]
        }

        html = render_template('contracts/preview_template.html', contract=preview_data)
        return html

    except Exception as e:
        current_app.logger.error(f"Error en preview: {e}")
        return f"<html><body style='color:red;padding:20px;font-family:sans-serif;'><h3>Error al generar preview</h3><p>{str(e)}</p></body></html>", 500


# =============================================================================
# API: EXTRACCIÓN OCR PARA AUTOCOMPLETADO (Drag & Drop)
# =============================================================================
@contract_builder_bp.route('/api/ocr-extract', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def api_ocr_extract():
    """
    Recibe un PDF vía AJAX (drag & drop), ejecuta OCR, parsea los datos
    y devuelve un JSON con los campos detectados para autocompletar el formulario.
    Si el prestador o departamento no existen, los crea automáticamente en la BD.
    """
    if 'contract_pdf' not in request.files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo.'}), 400

    file = request.files['contract_pdf']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Archivo vacío.'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Solo se permiten archivos PDF.'}), 400

    temp_path = None
    try:
        # Guardar temporalmente
        temp_dir = tempfile.gettempdir()
        temp_filename = f"ocr_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        temp_path = os.path.join(temp_dir, temp_filename)
        file.save(temp_path)

        # Extraer texto con OCR
        extracted_text = extract_text_from_pdf(temp_path)

        # Parsear datos estructurados
        parsed = parse_contract_data(extracted_text)

        # ── Buscar o AUTO-CREAR prestador ────────────────────────────────────
        provider_match = None
        if parsed.get('rut'):
            provider = ServiceProvider.query.filter(
                ServiceProvider.rut.ilike(f"%{parsed['rut']}%")
            ).first()

            # Auto-crear si no existe y tenemos datos suficientes
            if not provider and parsed.get('full_name'):
                try:
                    name_parts = parsed['full_name'].strip().split()
                    if len(name_parts) >= 2:
                        # Convención chilena: última palabra = maternal, penúltima = paternal, resto = first_name
                        maternal_last_name = name_parts[-1]
                        paternal_last_name = name_parts[-2]
                        first_name = ' '.join(name_parts[:-2]) if len(name_parts) > 2 else name_parts[0]

                        provider = ServiceProvider(
                            rut=parsed['rut'],
                            first_name=first_name,
                            paternal_last_name=paternal_last_name,
                            maternal_last_name=maternal_last_name
                        )
                        db.session.add(provider)
                        db.session.flush()

                        log_action('PROVIDER_AUTO_CREATE', 'service_provider', provider.id,
                                   {'rut': parsed['rut'], 'source': 'ocr_extract'})
                except Exception as create_err:
                    current_app.logger.warning(f"No se pudo auto-crear prestador: {create_err}")
                    db.session.rollback()

            if provider:
                provider_match = {
                    'id': provider.id,
                    'name': provider.full_name,
                    'rut': provider.rut
                }

        # ── Buscar o AUTO-CREAR departamento ──────────────────────────────────
        dept_match = None
        if parsed.get('department_name'):
            dept = Department.query.filter(
                Department.name.ilike(f"%{parsed['department_name']}%")
            ).first()
            if not dept:
                dept = Department.query.filter(
                    Department.code.ilike(f"%{parsed['department_name'][:6]}%")
                ).first()

            # Auto-crear si no existe
            if not dept:
                try:
                    dept_name = parsed['department_name'].strip()
                    # Generar código automático: primeras letras de cada palabra (máx 10 chars)
                    words = dept_name.split()
                    if len(words) >= 2:
                        code = ''.join(w[0] for w in words if w)[:10].upper()
                    else:
                        code = dept_name[:6].upper()

                    # Verificar que el código no exista ya
                    existing_code = Department.query.filter_by(code=code).first()
                    if existing_code:
                        code = code[:5] + str(Department.query.count() + 1)

                    dept = Department(
                        code=code,
                        name=dept_name,
                        is_active=1
                    )
                    db.session.add(dept)
                    db.session.flush()

                    log_action('DEPARTMENT_AUTO_CREATE', 'department', dept.id,
                               {'code': code, 'name': dept_name, 'source': 'ocr_extract'})
                except Exception as create_err:
                    current_app.logger.warning(f"No se pudo auto-crear departamento: {create_err}")
                    db.session.rollback()

            if dept:
                dept_match = {
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code
                }

        return jsonify({
            'success': True,
            'extracted_text': extracted_text,
            'parsed': parsed,
            'provider_match': provider_match,
            'department_match': dept_match
        })

    except Exception as e:
        current_app.logger.error(f"Error OCR extract: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

# =============================================================================
# API: BUSCADOR DINÁMICO DE PRESTADORES + ÚLTIMO CONTRATO
# =============================================================================
@contract_builder_bp.route('/api/search-provider-contract', methods=['GET'])
@login_required
def search_provider_contract():
    """
    Busca prestadores por nombre o RUT y devuelve, para cada uno,
    los datos de su último contrato registrado (si existe).
    Usado por el buscador dinámico del armador de contratos.
    """
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'success': True, 'providers': []})

    providers = ServiceProvider.query.filter(
        db.or_(
            ServiceProvider.rut.ilike(f'%{query}%'),
            ServiceProvider.first_name.ilike(f'%{query}%'),
            ServiceProvider.paternal_last_name.ilike(f'%{query}%'),
            ServiceProvider.maternal_last_name.ilike(f'%{query}%')
        )
    ).limit(8).all()

    results = []
    for p in providers:
        # Buscar el último contrato del prestador
        last_contract = Contract.query.filter_by(provider_id=p.id)\
            .order_by(Contract.id.desc()).first()

        provider_data = {
            'id': p.id,
            'rut': p.rut,
            'full_name': p.full_name,
            'last_contract': None
        }

        if last_contract:
            functions = ContractFunction.query.filter_by(
                contract_id=last_contract.id
            ).order_by(ContractFunction.function_order).all()

            dept = Department.query.get(last_contract.department_id)

            provider_data['last_contract'] = {
                'id': last_contract.id,  # ← ESTA LÍNEA NUEVA
                'contract_number': last_contract.contract_number,
                'position_title': last_contract.position_title,
                'program_name': last_contract.program_name or '',
                'monthly_amount_gross': last_contract.monthly_amount_gross,
                'total_contract_amount': last_contract.total_contract_amount,
                'start_date': last_contract.start_date.strftime('%Y-%m-%d') if last_contract.start_date else '',
                'end_date': last_contract.end_date.strftime('%Y-%m-%d') if last_contract.end_date else '',
                'decline_number': last_contract.decline_number or '',
                'decline_date': last_contract.decline_date.strftime('%Y-%m-%d') if last_contract.decline_date else '',
                'department_id': last_contract.department_id,
                'department_code': dept.code if dept else '',
                'department_name': dept.name if dept else '',
                'functions': [
                    {'order': f.function_order, 'description': f.function_description}
                    for f in functions
                ]
            }

        results.append(provider_data)

    return jsonify({'success': True, 'providers': results})

# =============================================================================
# APIs AUXILIARES
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