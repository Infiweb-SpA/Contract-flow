from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.utils import secure_filename
from app import db
from app.auth.utils import login_required, role_required, get_current_user
from app.models.user import Department
from app.models.provider import ServiceProvider
from app.models.contract import Contract, ContractFunction
from app.models.decree import (DECREE_TYPE_LABELS, ContractDecree, DecreeTemplate,
                               VISTOS_SELECTABLE_TYPES, order_vistos)
from app.services.audit_service import log_action, get_contract_audit_trail
from app.services.pdf_generator import generate_contract_html, make_pdf_response, generate_contract_preview
from app.services.ocr_service import extract_text_from_pdf, parse_contract_data, format_date_es, OCRCancelledException
import os
import tempfile
import uuid
import threading

contract_builder_bp = Blueprint('contract_builder', __name__, url_prefix='/contracts')


# =============================================================================
# REGISTRY DE CANCELACIÓN OCR (thread-safe)
# =============================================================================
# Diccionario que almacena tokens de OCR en curso.
# Cuando el usuario cancela, el frontend envía su token al endpoint
# /api/ocr-cancel, y se marca como True. El bucle de OCR consulta
# este diccionario entre cada página y detiene el procesamiento.
_ocr_cancel_registry = {}
_ocr_cancel_lock = threading.Lock()


def _register_cancel_token(token):
    """Registra un nuevo token como activo (no cancelado)."""
    with _ocr_cancel_lock:
        _ocr_cancel_registry[token] = False


def _mark_cancelled(token):
    """Marca un token como cancelado."""
    with _ocr_cancel_lock:
        if token in _ocr_cancel_registry:
            _ocr_cancel_registry[token] = True
            return True
        return False


def _is_token_cancelled(token):
    """Verifica si un token fue marcado como cancelado."""
    with _ocr_cancel_lock:
        return _ocr_cancel_registry.get(token, False)


def _unregister_cancel_token(token):
    """Limpia un token del registry (tanto si fue exitoso como cancelado)."""
    with _ocr_cancel_lock:
        _ocr_cancel_registry.pop(token, None)


# =============================================================================
# REGISTRY DE PROGRESO OCR (thread-safe)
# =============================================================================
# Almacena el progreso real del procesamiento OCR (0-100) por token,
# de modo que el frontend pueda consultarlo vía polling mientras el
# servidor extrae el texto página a página.
_ocr_progress_registry = {}
_ocr_progress_lock = threading.Lock()


def _register_ocr_progress(token):
    """Registra un token con progreso inicial 0%."""
    with _ocr_progress_lock:
        _ocr_progress_registry[token] = {
            'progress': 0,
            'status': 'processing',
            'total_pages': 0,
            'current_page': 0,
        }


def _update_ocr_progress(token, progress=None, status=None,
                          total_pages=None, current_page=None):
    """Actualiza el progreso real de un token en curso."""
    with _ocr_progress_lock:
        entry = _ocr_progress_registry.get(token)
        if entry is None:
            return
        if progress is not None:
            entry['progress'] = max(0, min(100, int(progress)))
        if status is not None:
            entry['status'] = status
        if total_pages is not None:
            entry['total_pages'] = int(total_pages)
        if current_page is not None:
            entry['current_page'] = int(current_page)


def _get_ocr_progress(token):
    """Devuelve el estado de progreso de un token (o None si no existe)."""
    with _ocr_progress_lock:
        entry = _ocr_progress_registry.get(token)
        return dict(entry) if entry else None


def _unregister_ocr_progress(token):
    """Limpia el progreso de un token (proceso finalizado)."""
    with _ocr_progress_lock:
        _ocr_progress_registry.pop(token, None)


# =============================================================================
# DECRETOS / VISTOS PREVIOS (helpers compartidos create/edit)
# =============================================================================
def _load_templates_for_context(year=None):
    """
    Plantillas activas del catálogo para precargar el formulario.
    Solo expone tipos seleccionables del bloque VISTOS (BASE_LEGAL y
    CONTRATO_ACTUAL se inyectan fijados en la plantilla del documento).
    Si se recibe `year`, filtra por ese año presupuestario (o plantillas
    sin año, que aplican a todos los años).
    """
    target_year = year or datetime.now().year
    return DecreeTemplate.query.filter(
        DecreeTemplate.is_active.is_(True),
        DecreeTemplate.decree_type.in_(list(VISTOS_SELECTABLE_TYPES)),
        db.or_(DecreeTemplate.year == target_year, DecreeTemplate.year.is_(None))
    ).order_by(DecreeTemplate.id).all()


def _collect_decrees_from_form():
    """
    Lee los decretos del formulario (create/edit):
      - decree_template_ids[]: plantillas del catálogo marcadas → copies.
      - decree_type[]/decree_number[]/decree_date[]/decree_description[]:
        filas manuales del prestador.
    Retorna (templates_ids, manual_rows) donde manual_rows es una lista de
    dicts {decree_type, decree_number, decree_date, description}.
    """
    template_ids = request.form.getlist('decree_template_ids')

    manual_rows = []
    types = request.form.getlist('decree_type[]')
    numbers = request.form.getlist('decree_number[]')
    dates = request.form.getlist('decree_date[]')
    descs = request.form.getlist('decree_description[]')

    for idx, desc in enumerate(descs):
        clean_desc = desc.strip()
        if not clean_desc:
            continue

        decree_type = types[idx] if idx < len(types) else 'OTRO'
        if decree_type not in DECREE_TYPE_LABELS:
            decree_type = 'OTRO'

        number = numbers[idx].strip() if idx < len(numbers) else ''
        decree_date = None
        if idx < len(dates) and dates[idx]:
            try:
                decree_date = datetime.strptime(dates[idx], '%Y-%m-%d').date()
            except ValueError:
                decree_date = None

        manual_rows.append({
            'decree_type': decree_type,
            'decree_number': number or None,
            'decree_date': decree_date,
            'description': clean_desc,
        })

    return template_ids, manual_rows


def _save_contract_decrees(contract):
    """
    Reemplaza los decretos/VISTOS de un contrato según el formulario.
    Las plantillas se COPIAN como snapshot (origin PLANTILLA); las filas
    manuales se guardan con origin MANUAL en el orden de ingreso.
    """
    template_ids, manual_rows = _collect_decrees_from_form()

    ContractDecree.query.filter_by(contract_id=contract.id).delete()

    templates = []
    if template_ids:
        templates = DecreeTemplate.query.filter(
            DecreeTemplate.id.in_([int(t) for t in template_ids if str(t).isdigit()])
        ).filter_by(is_active=True).order_by(DecreeTemplate.id).all()

    order = 0
    for tpl in templates:
        order += 1
        db.session.add(ContractDecree(
            contract_id=contract.id,
            template_id=tpl.id,
            decree_type=tpl.decree_type,
            decree_number=tpl.decree_number,
            decree_date=tpl.decree_date,
            description=tpl.description,
            origin='PLANTILLA',
            display_order=order,
        ))

    for row in manual_rows:
        order += 1
        db.session.add(ContractDecree(
            contract_id=contract.id,
            decree_type=row['decree_type'],
            decree_number=row['decree_number'],
            decree_date=row['decree_date'],
            description=row['description'],
            origin='MANUAL',
            display_order=order,
        ))

    return len(templates), len(manual_rows)


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

            # ── Nuevos campos (estructura Freire) ──
            contract_date_str = request.form.get('contract_date')
            budget_account = request.form.get('budget_account', '').strip()
            sub_program = request.form.get('sub_program', '').strip()
            cost_center = request.form.get('cost_center', '').strip()
            payment_modality = request.form.get('payment_modality', 'MENSUAL_FIJO').strip()

            # ── Datos del Decreto Alcaldicio (estructura Cunco) ──
            provider_address = request.form.get('provider_address', '').strip() or None
            provider_comuna = request.form.get('provider_comuna', '').strip() or None
            try:
                hours_weekly = int(request.form.get('hours_weekly')) or None
            except (TypeError, ValueError):
                hours_weekly = None
            total_amount_words = request.form.get('total_amount_words', '').strip() or None
            # ── Firmas del decreto (dataURL PNG dibujado en el modal) ──
            MAX_SIG_LEN = 300000
            mayor_signature = (request.form.get('mayor_signature') or '').strip()[:MAX_SIG_LEN] or None
            secretary_signature = (request.form.get('secretary_signature') or '').strip()[:MAX_SIG_LEN] or None

            # ── Trazabilidad: registrar quién crea ──
            current_user = get_current_user()

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
                contract_date=datetime.strptime(contract_date_str, '%Y-%m-%d').date() if contract_date_str else None,
                budget_account=budget_account or None,
                sub_program=sub_program or None,
                cost_center=cost_center or None,
                payment_modality=payment_modality,
                provider_address=provider_address,
                provider_comuna=provider_comuna,
                hours_weekly=hours_weekly,
                total_amount_words=total_amount_words,
                mayor_signature=mayor_signature,
                secretary_signature=secretary_signature,
                status='BORRADOR',
                created_by_user_id=current_user.id if current_user else None,
                last_modified_by_user_id=current_user.id if current_user else None,
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
                        function_description=clean_desc
                    )
                    db.session.add(func)

            # ── Decretos y Antecedentes Previos (VISTOS) ──
            tpl_count, manual_count = _save_contract_decrees(new_contract)

            db.session.commit()

            log_action(
                action='CONTRACT_CREATE',
                entity_type='contract',
                entity_id=new_contract.id,
                payload={'contract_number': contract_number, 'provider_id': provider_id}
            )
            if tpl_count or manual_count:
                log_action(
                    action='CONTRACT_DECREE_UPDATE',
                    entity_type='contract',
                    entity_id=new_contract.id,
                    payload={'templates': tpl_count, 'manual': manual_count}
                )

            flash(f'Contrato N° {contract_number} creado exitosamente.', 'success')
            return redirect(url_for('contract_builder.detail', contract_id=new_contract.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al armar el contrato: {str(e)}', 'danger')

    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()
    return render_template('contracts/create.html', providers=providers, departments=departments,
                           decree_templates=_load_templates_for_context(),
                           decree_type_options=DECREE_TYPE_LABELS)


# =============================================================================
# API: PLANTILLAS DE DECRETOS POR AÑO (reactividad del paso 4 al año de inicio)
# =============================================================================
@contract_builder_bp.route('/api/decree-templates')
@login_required
def api_decree_templates():
    year = request.args.get('year', type=int)
    templates = _load_templates_for_context(year=year)
    target_year = year or datetime.now().year

    def _tpl_json(t):
        return {
            'id': t.id,
            'decree_type': t.decree_type,
            'decree_type_label': t.decree_type_label,
            'decree_number': t.decree_number or '',
            'decree_date': t.decree_date.strftime('%Y-%m-%d') if t.decree_date else '',
            'description': t.description,
            'year': t.year,
        }

    # Plantillas activas de OTROS años (visibles en un grupo colapsable para
    # que nada del catálogo quede "invisible" al armar el contrato).
    other_years = DecreeTemplate.query.filter(
        DecreeTemplate.is_active.is_(True),
        DecreeTemplate.decree_type.in_(list(VISTOS_SELECTABLE_TYPES)),
        DecreeTemplate.year.isnot(None),
        DecreeTemplate.year != target_year,
    ).order_by(DecreeTemplate.year, DecreeTemplate.id).all()

    return jsonify({
        'success': True,
        'year': target_year,
        'templates': [_tpl_json(t) for t in templates],
        'other_years': [_tpl_json(t) for t in other_years],
    })


# =============================================================================
# DETALLE DEL CONTRATO
# =============================================================================
@contract_builder_bp.route('/<int:contract_id>')
@login_required
def detail(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    audit_trail = get_contract_audit_trail(contract_id)
    return render_template('contracts/detail.html', contract=contract, audit_trail=audit_trail)


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

            contract_date_str = request.form.get('contract_date')
            contract.contract_date = datetime.strptime(contract_date_str, '%Y-%m-%d').date() if contract_date_str else None
            contract.budget_account = request.form.get('budget_account', '').strip() or None
            contract.sub_program = request.form.get('sub_program', '').strip() or None
            contract.cost_center = request.form.get('cost_center', '').strip() or None
            contract.payment_modality = request.form.get('payment_modality', 'MENSUAL_FIJO').strip()
            contract.provider_address = request.form.get('provider_address', '').strip() or None
            contract.provider_comuna = request.form.get('provider_comuna', '').strip() or None
            try:
                contract.hours_weekly = int(request.form.get('hours_weekly')) or None
            except (TypeError, ValueError):
                contract.hours_weekly = None
            contract.total_amount_words = request.form.get('total_amount_words', '').strip() or None
            # ── Firmas del decreto (dataURL PNG dibujado en el modal) ──
            MAX_SIG_LEN = 300000
            contract.mayor_signature = (request.form.get('mayor_signature') or '').strip()[:MAX_SIG_LEN] or None
            contract.secretary_signature = (request.form.get('secretary_signature') or '').strip()[:MAX_SIG_LEN] or None

            current_user = get_current_user()
            contract.last_modified_by_user_id = current_user.id if current_user else None

            ContractFunction.query.filter_by(contract_id=contract.id).delete()
            functions = request.form.getlist('functions[]')
            for index, func_desc in enumerate(functions, start=1):
                clean_desc = func_desc.strip()
                if clean_desc:
                    db.session.add(ContractFunction(
                        contract_id=contract.id,
                        function_order=index,
                        function_description=clean_desc
                    ))

            # ── Decretos y Antecedentes Previos (VISTOS) ──
            tpl_count, manual_count = _save_contract_decrees(contract)

            db.session.commit()
            log_action('CONTRACT_UPDATE', 'contract', contract.id, {'contract_number': contract.contract_number})
            if tpl_count or manual_count:
                log_action(
                    action='CONTRACT_DECREE_UPDATE',
                    entity_type='contract',
                    entity_id=contract.id,
                    payload={'templates': tpl_count, 'manual': manual_count}
                )
            flash('Contrato actualizado exitosamente.', 'success')
            return redirect(url_for('contract_builder.detail', contract_id=contract.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')

    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()
    return render_template('contracts/edit.html', contract=contract, providers=providers,
                           departments=departments,
                           decree_templates=_load_templates_for_context(
                               year=contract.start_date.year if contract.start_date else None),
                           decree_type_options=DECREE_TYPE_LABELS)


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
        current_user = get_current_user()
        contract.last_modified_by_user_id = current_user.id if current_user else None

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

                current_user = get_current_user()

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
                    status='INGRESADO',
                    created_by_user_id=current_user.id if current_user else None,
                    last_modified_by_user_id=current_user.id if current_user else None,
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
                                function_description=line
                            ))

                    # ── VISTOS: deCRETOS y antecedentes detectados por OCR ──
                    from app.services.ocr_service import extract_decrees_vistos
                    for idx, dec in enumerate(extract_decrees_vistos(extracted_text), start=1):
                        decree_date = None
                        if dec.get('decree_date'):
                            try:
                                decree_date = datetime.strptime(dec['decree_date'], '%Y-%m-%d').date()
                            except (ValueError, TypeError):
                                decree_date = None
                        db.session.add(ContractDecree(
                            contract_id=new_contract.id,
                            decree_type=dec['decree_type'] if dec['decree_type'] in DECREE_TYPE_LABELS else 'OTRO',
                            decree_number=dec.get('decree_number'),
                            decree_date=decree_date,
                            description=dec['description'],
                            origin='MANUAL',
                            display_order=idx,
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
    try:
        data = request.get_json() or {}

        provider_name = data.get('provider_name', '____________________')
        provider_rut = data.get('provider_rut', '____________________')
        provider_profession = ''
        provider_nationality = ''
        department_name = data.get('department_name', '____________________')

        # ── Datos del Decreto Alcaldicio (domicilio/comuna para página 2) ──
        provider_address = (data.get('provider_address') or '').strip()
        provider_comuna = (data.get('provider_comuna') or '').strip()

        if data.get('provider_id'):
            provider = ServiceProvider.query.get(data['provider_id'])
            if provider:
                provider_name = provider.full_name
                provider_rut = provider.rut
                provider_profession = provider.profession_or_trade or ''
                provider_nationality = provider.nationality or ''
                # Domicilio desde la ficha si el formulario no lo definió
                if not provider_address:
                    provider_address = provider.address or ''

        if data.get('department_id'):
            dept = Department.query.get(data['department_id'])
            if dept:
                department_name = dept.name

        start_date_str = format_date_es(data.get('start_date'))
        end_date_str = format_date_es(data.get('end_date'))
        decline_date_str = format_date_es(data.get('decline_date'))
        contract_date_str = format_date_es(data.get('contract_date'))

        monto = data.get('monthly_amount_gross')
        monto_str = "{:,.0f}".format(float(monto)) if monto else '__________'

        total = data.get('total_contract_amount')
        total_str = "{:,.0f}".format(float(total)) if total else None

        sd = data.get('start_date')
        ed = data.get('end_date')
        duration_months = None
        if sd and ed:
            try:
                sd_dt = datetime.strptime(sd, '%Y-%m-%d')
                ed_dt = datetime.strptime(ed, '%Y-%m-%d')
                duration_months = (ed_dt.year - sd_dt.year) * 12 + (ed_dt.month - sd_dt.month) + 1
            except:
                pass

        # ── VISTOS agrupados por tipo (solo los 7 tipos admitidos + OTRO) ──
        decrees_clean = [
            {
                'decree_type': d.get('decree_type', 'OTRO'),
                'decree_number': d.get('decree_number'),
                'decree_date': d.get('decree_date'),
                'description': (d.get('description') or '').strip(),
            }
            for d in (data.get('decrees') or [])
            if (d.get('description') or '').strip()
        ]
        vistos = order_vistos(decrees_clean)

        # ── Datos Decreto Alcaldicio (página 2, estructura Cunco) ──
        try:
            hours_weekly = int(data.get('hours_weekly')) or None
        except (TypeError, ValueError):
            hours_weekly = None
        try:
            budget_year = datetime.strptime(sd, '%Y-%m-%d').year if sd else datetime.now().year
        except (ValueError, TypeError):
            budget_year = datetime.now().year

        preview_data = {
            'contract_number': data.get('contract_number', 'CT-XXXX-XXX') or 'CT-XXXX-XXX',
            'position_title': data.get('position_title', '____________________'),
            'program_name': data.get('program_name', 'Gestión Municipal'),
            'monthly_amount_gross': monto_str,
            'total_contract_amount': total_str,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'decline_number': data.get('decline_number', ''),
            'decline_date': decline_date_str,
            'contract_date': contract_date_str,
            'created_at': datetime.now(),
            'provider_name': provider_name,
            'provider_rut': provider_rut,
            'provider_profession': provider_profession,
            'provider_nationality': provider_nationality,
            'department_name': department_name,
            'budget_account': data.get('budget_account', ''),
            'sub_program': data.get('sub_program', ''),
            'cost_center': data.get('cost_center', ''),
            'payment_modality': data.get('payment_modality', 'MENSUAL_FIJO'),
            'duration_months': duration_months,
            'functions': [f.strip() for f in data.get('functions', []) if f.strip()],
            'decrees': decrees_clean,
            # VISTOS filtrados + ordenados por decreto_type (bloque página 1)
            'vistos': vistos,
            # ── Datos Decreto Alcaldicio (página 2, estructura Cunco) ──
            'provider_address': provider_address,
            'provider_comuna': provider_comuna,
            'hours_weekly': hours_weekly,
            'total_amount_words': (data.get('total_amount_words') or '').strip(),
            # ── Firmas del decreto (dataURL PNG o None) ──
            'mayor_signature': data.get('mayor_signature') or None,
            'secretary_signature': data.get('secretary_signature') or None,
            'budget_year': budget_year,
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

        html = render_template('contracts/preview_template.html', contract=preview_data)
        return html

    except Exception as e:
        current_app.logger.error(f"Error en preview: {e}")
        return f"<html><body style='color:red;padding:20px;font-family:sans-serif;'><h3>Error al generar preview</h3><p>{str(e)}</p></body></html>", 500


# =============================================================================
# API: EXTRACCIÓN OCR PARA AUTOCOMPLETADO (Drag & Drop) — CON CANCELACIÓN
# =============================================================================
@contract_builder_bp.route('/api/ocr-extract', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def api_ocr_extract():
    if 'contract_pdf' not in request.files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo.'}), 400

    file = request.files['contract_pdf']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Archivo vacío.'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Solo se permiten archivos PDF.'}), 400

    # ── El cancel_token viene del frontend (generado con crypto.randomUUID()) ──
    cancel_token = request.form.get('cancel_token', '').strip()
    if not cancel_token:
        cancel_token = uuid.uuid4().hex  # Fallback por seguridad

    _register_cancel_token(cancel_token)
    _register_ocr_progress(cancel_token)

    def is_cancelled():
        return _is_token_cancelled(cancel_token)

    def on_progress(info):
        """Reporta el progreso real del procesamiento OCR."""
        _update_ocr_progress(
            cancel_token,
            progress=info.get('progress'),
            total_pages=info.get('total_pages'),
            current_page=info.get('current_page'),
        )

    temp_path = None
    try:
        temp_dir = tempfile.gettempdir()
        temp_filename = f"ocr_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        temp_path = os.path.join(temp_dir, temp_filename)
        file.save(temp_path)

        _update_ocr_progress(cancel_token, progress=2, status='processing')

        extracted_text = extract_text_from_pdf(temp_path, is_cancelled=is_cancelled,
                                               on_progress=on_progress)

        _update_ocr_progress(cancel_token, progress=96, status='parsing')
        parsed = parse_contract_data(extracted_text)
        _update_ocr_progress(cancel_token, progress=99, status='parsing')

        # ── Buscar o AUTO-CREAR prestador ──
        provider_match = None
        provider_was_created = False
        if parsed.get('rut'):
            provider = ServiceProvider.query.filter(
                ServiceProvider.rut.ilike(f"%{parsed['rut']}%")
            ).first()

            if not provider and parsed.get('full_name'):
                try:
                    name_parts = parsed['full_name'].strip().split()
                    if len(name_parts) >= 2:
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
                        provider_was_created = True

                        log_action('PROVIDER_AUTO_CREATE', 'service_provider', provider.id,
                                   {'rut': parsed['rut'], 'source': 'ocr_extract'})
                except Exception as create_err:
                    current_app.logger.warning(f"No se pudo auto-crear prestador: {create_err}")
                    db.session.rollback()

            if provider:
                provider_match = {
                    'id': provider.id,
                    'name': provider.full_name,
                    'rut': provider.rut,
                    'auto_created': provider_was_created
                }

        # ── Buscar o AUTO-CREAR departamento ──
        dept_match = None
        dept_was_created = False
        if parsed.get('department_name'):
            dept = Department.query.filter(
                Department.name.ilike(f"%{parsed['department_name']}%")
            ).first()
            if not dept:
                dept = Department.query.filter(
                    Department.code.ilike(f"%{parsed['department_name'][:6]}%")
                ).first()

            if not dept:
                try:
                    dept_name = parsed['department_name'].strip()
                    words = dept_name.split()
                    if len(words) >= 2:
                        code = ''.join(w[0] for w in words if w)[:10].upper()
                    else:
                        code = dept_name[:6].upper()

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
                    dept_was_created = True

                    log_action('DEPARTMENT_AUTO_CREATE', 'department', dept.id,
                               {'code': code, 'name': dept_name, 'source': 'ocr_extract'})
                except Exception as create_err:
                    current_app.logger.warning(f"No se pudo auto-crear departamento: {create_err}")
                    db.session.rollback()

            if dept:
                dept_match = {
                    'id': dept.id,
                    'name': dept.name,
                    'code': dept.code,
                    'auto_created': dept_was_created
                }

        _update_ocr_progress(cancel_token, progress=100, status='done')

        return jsonify({
            'success': True,
            'cancel_token': cancel_token,
            'extracted_text': extracted_text,
            'parsed': parsed,
            'provider_match': provider_match,
            'department_match': dept_match
        })

    except OCRCancelledException:
        current_app.logger.info(f"OCR cancelado por el usuario (token: {cancel_token[:8]}...)")
        _update_ocr_progress(cancel_token, status='cancelled')
        return jsonify({
            'success': False,
            'status_text': 'cancelled',
            'message': 'El procesamiento OCR fue cancelado por el usuario.'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error OCR extract: {e}")
        _update_ocr_progress(cancel_token, status='error')
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        _unregister_cancel_token(cancel_token)
        _unregister_ocr_progress(cancel_token)


# =============================================================================
# API: PROGRESO REAL DEL PROCESAMIENTO OCR (polling)
# =============================================================================
@contract_builder_bp.route('/api/ocr-progress', methods=['GET'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def api_ocr_progress():
    """
    Devuelve el progreso real (0-100) del procesamiento OCR en curso.
    El frontend lo consulta por polling mientras el servidor extrae el texto.
    """
    token = (request.args.get('token') or '').strip()
    if not token:
        return jsonify({'success': False, 'message': 'Token no proporcionado.'}), 400

    progress = _get_ocr_progress(token)
    if progress is None:
        # El proceso ya terminó (o nunca existió): no es un error para el cliente.
        return jsonify({
            'success': True,
            'found': False,
            'progress': 100,
            'status': 'done'
        })

    return jsonify({
        'success': True,
        'found': True,
        'progress': progress.get('progress', 0),
        'status': progress.get('status', 'processing'),
        'total_pages': progress.get('total_pages', 0),
        'current_page': progress.get('current_page', 0),
    })


# =============================================================================
# API: CANCELAR PROCESO OCR EN CURSO (NUEVO)
# =============================================================================
@contract_builder_bp.route('/api/ocr-cancel', methods=['POST'])
@login_required
def api_ocr_cancel():
    """
    Endpoint para cancelar un proceso OCR en curso.
    Recibe el cancel_token que se devolvió en la respuesta de /api/ocr-extract.
    El motor OCR verificará este token entre cada página y detendrá el procesamiento.
    """
    data = request.get_json() or {}
    cancel_token = data.get('cancel_token', '').strip()

    if not cancel_token:
        return jsonify({'success': False, 'message': 'Token de cancelación no proporcionado.'}), 400

    was_marked = _mark_cancelled(cancel_token)

    if was_marked:
        current_app.logger.info(f"Solicitud de cancelación OCR registrada (token: {cancel_token[:8]}...)")
        return jsonify({
            'success': True,
            'message': 'Solicitud de cancelación registrada. El proceso se detendrá en la próxima página.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'El token no existe o el proceso ya finalizó.'
        }), 404


# =============================================================================
# API: BUSCADOR DINÁMICO DE PRESTADORES + ÚLTIMO CONTRATO
# =============================================================================
@contract_builder_bp.route('/api/search-provider-contract', methods=['GET'])
@login_required
def search_provider_contract():
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
                'id': last_contract.id,
                'contract_number': last_contract.contract_number,
                'position_title': last_contract.position_title,
                'program_name': last_contract.program_name or '',
                'monthly_amount_gross': last_contract.monthly_amount_gross,
                'total_contract_amount': last_contract.total_contract_amount,
                'start_date': last_contract.start_date.strftime('%Y-%m-%d') if last_contract.start_date else '',
                'end_date': last_contract.end_date.strftime('%Y-%m-%d') if last_contract.end_date else '',
                'decline_number': last_contract.decline_number or '',
                'decline_date': last_contract.decline_date.strftime('%Y-%m-%d') if last_contract.decline_date else '',
                'contract_date': last_contract.contract_date.strftime('%Y-%m-%d') if last_contract.contract_date else '',
                'budget_account': last_contract.budget_account or '',
                'sub_program': last_contract.sub_program or '',
                'cost_center': last_contract.cost_center or '',
                'payment_modality': last_contract.payment_modality or 'MENSUAL_FIJO',
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
            'address': p.address or '',
            'profession_or_trade': p.profession_or_trade or ''
        })

    return jsonify({'success': True, 'providers': results})


@contract_builder_bp.route('/api/provider/<int:provider_id>/detail')
@login_required
def api_provider_detail(provider_id):
    provider = ServiceProvider.query.get_or_404(provider_id)
    return jsonify({
        'success': True,
        'provider': {
            'profession_or_trade': provider.profession_or_trade or '',
            'nationality': provider.nationality or '',
            'civil_status': provider.civil_status or '',
            'birth_date': str(provider.birth_date) if provider.birth_date else '',
            'bank_name': provider.bank_name or '',
            'account_type': provider.account_type or '',
            'account_number': provider.account_number or '',
            'address': provider.address or '',
        }
    })


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
            profession_or_trade=data.get('profession_or_trade', '').strip(),
            nationality=data.get('nationality', 'Chilena').strip(),
            civil_status=data.get('civil_status', '').strip(),
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data.get('birth_date') else None,
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