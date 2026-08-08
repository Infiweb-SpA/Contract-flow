# app/routes/payments.py
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app import db
from app.auth.utils import login_required, role_required, get_current_user
from app.models.contract import Contract, ContractFunction
from app.models.payment import MonthlyPayment, PaymentFunctionChecklist
from app.models.user import User
from app.services.audit_service import log_action
from app.services.ocr_service import extract_text_from_pdf

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


# =============================================================================
# BANDEJA DE PAGOS MENSUALES
# =============================================================================
@payments_bp.route('/')
@login_required
def bandeja():
    user = get_current_user()
    status_filter = request.args.get('status', '')

    query = MonthlyPayment.query.join(Contract).join(Contract.provider)

    # Si NO hay filtro de estado: mostrar bandeja de trabajo del rol (pendientes)
    if not status_filter:
        if user.role == 'JEFE_DEPTO':
            query = query.filter(Contract.department_id == user.department_id)
            query = query.filter(MonthlyPayment.approval_status.in_(['PENDIENTE_REVISION', 'OBSERVADO']))
        elif user.role == 'ADMIN_RRHH':
            query = query.filter(MonthlyPayment.approval_status.in_(['VISADO_JEFE_DEPTO', 'OBSERVADO']))
        elif user.role == 'FINANZAS_CONTROL':
            query = query.filter(MonthlyPayment.approval_status.in_(['APROBADO_RRHH', 'OBSERVADO']))
        # SUPERADMIN: ve todo sin filtrar
    else:
        # Si hay filtro de estado: mostrar TODOS los pagos con ese estado (historial)
        query = query.filter(MonthlyPayment.approval_status == status_filter)

    payments = query.order_by(MonthlyPayment.payment_year.desc(), MonthlyPayment.payment_month.desc()).all()
    
    # ← AQUÍ ESTABA EL ERROR: faltaba pasar 'user'
    return render_template('payments/bandejas.html', payments=payments, status_filter=status_filter, user=user)

# =============================================================================
# CREAR PAGO MENSUAL DESDE CONTRATO
# =============================================================================
@payments_bp.route('/contract/<int:contract_id>/create', methods=['POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def create_payment(contract_id):
    try:
        contract = Contract.query.get_or_404(contract_id)
        year = int(request.form.get('payment_year')) if request.form.get('payment_year') else datetime.now().year
        month = int(request.form.get('payment_month')) if request.form.get('payment_month') else datetime.now().month

        existing = MonthlyPayment.query.filter_by(
            contract_id=contract_id, payment_year=year, payment_month=month
        ).first()
        if existing:
            flash('Ya existe un pago registrado para este período.', 'warning')
            return redirect(url_for('payments.review', payment_id=existing.id))

        payment = MonthlyPayment(
            contract_id=contract_id,
            payment_year=year,
            payment_month=month,
            amount_to_pay=contract.monthly_amount_gross,
            approval_status='PENDIENTE_REVISION'
        )
        db.session.add(payment)
        db.session.flush()

        for func in contract.functions:
            db.session.add(PaymentFunctionChecklist(
                monthly_payment_id=payment.id,
                contract_function_id=func.id,
                status='CUMPLIDO',
                comments=''
            ))

        db.session.commit()
        log_action('PAYMENT_CREATE', 'monthly_payment', payment.id, {'period': f'{month}/{year}'})
        flash(f'Pago {month}/{year} creado y enviado a revisión.', 'success')
        return redirect(url_for('payments.review', payment_id=payment.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear pago: {str(e)}', 'danger')
        return redirect(url_for('contract_builder.detail', contract_id=contract_id))


# =============================================================================
# REVISIÓN DE PAGO CON CHECKLIST
# =============================================================================
@payments_bp.route('/<int:payment_id>/review', methods=['GET', 'POST'])
@login_required
def review(payment_id):
    payment = MonthlyPayment.query.get_or_404(payment_id)
    contract = Contract.query.get_or_404(payment.contract_id)
    user = get_current_user()

    if request.method == 'POST':
        try:
            checklist_ids = request.form.getlist('checklist_id[]')
            statuses = request.form.getlist('checklist_status[]')
            comments = request.form.getlist('checklist_comments[]')

            for cid, st, co in zip(checklist_ids, statuses, comments):
                item = PaymentFunctionChecklist.query.get(int(cid))
                if item and item.monthly_payment_id == payment.id:
                    item.status = st
                    item.comments = co.strip()

            if 'report_file' in request.files:
                file = request.files['report_file']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(
                        f"informe_ct_{payment.contract_id}_{payment.payment_year}_{payment.payment_month}_{file.filename}"
                    )
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    payment.report_file_path = filepath

            db.session.commit()
            flash('Checklist y observaciones guardadas.', 'success')
            return redirect(url_for('payments.review', payment_id=payment.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar revisión: {str(e)}', 'danger')

    checklist_items = PaymentFunctionChecklist.query.filter_by(monthly_payment_id=payment.id).all()
    functions_map = {cf.id: cf for cf in contract.functions}

    pdf_url = None
    if payment.report_file_path and os.path.exists(payment.report_file_path):
        rel = os.path.relpath(payment.report_file_path, current_app.root_path)
        pdf_url = url_for('static', filename=rel.replace('app/static/', ''))

    return render_template(
        'payments/review.html',
        payment=payment,
        contract=contract,
        checklist_items=checklist_items,
        functions_map=functions_map,
        pdf_url=pdf_url,
        user=user
    )


# =============================================================================
# APROBAR / RECHAZAR / OBSERVAR PAGO
# =============================================================================
@payments_bp.route('/<int:payment_id>/approve', methods=['POST'])
@login_required
def approve_payment(payment_id):
    payment = MonthlyPayment.query.get_or_404(payment_id)
    user = get_current_user()
    action = request.form.get('action')
    obs = request.form.get('observations', '').strip()

    try:
        if action == 'approve':
            if user.role == 'JEFE_DEPTO' and payment.approval_status in ['PENDIENTE_REVISION', 'OBSERVADO']:
                payment.approval_status = 'VISADO_JEFE_DEPTO'
                payment.reviewed_by_depto_user_id = user.id
                log_action('PAYMENT_VISADO_DEPTO', 'monthly_payment', payment.id, {'by': user.id})
                flash('Pago visado por Jefe de Departamento.', 'success')

            elif user.role == 'ADMIN_RRHH' and payment.approval_status in ['VISADO_JEFE_DEPTO', 'OBSERVADO']:
                payment.approval_status = 'APROBADO_RRHH'
                payment.approved_by_rrhh_user_id = user.id
                log_action('PAYMENT_APROBADO_RRHH', 'monthly_payment', payment.id, {'by': user.id})
                flash('Pago aprobado por RRHH.', 'success')

            elif user.role == 'FINANZAS_CONTROL' and payment.approval_status in ['APROBADO_RRHH', 'OBSERVADO']:
                payment.approval_status = 'APROBADO_FINANZAS'
                payment.approved_by_finanzas_user_id = user.id
                log_action('PAYMENT_APROBADO_FINANZAS', 'monthly_payment', payment.id, {'by': user.id})
                flash('Pago aprobado por Finanzas. Listo para liquidación.', 'success')

            else:
                flash('No tiene permisos para aprobar en esta etapa o el estado no corresponde.', 'danger')

        elif action == 'reject':
            payment.approval_status = 'RECHAZADO'
            payment.rejection_observations = obs
            log_action('PAYMENT_RECHAZADO', 'monthly_payment', payment.id, {'by': user.id, 'reason': obs})
            flash('Pago rechazado.', 'warning')

        elif action == 'observe':
            payment.approval_status = 'OBSERVADO'
            payment.rejection_observations = obs
            log_action('PAYMENT_OBSERVADO', 'monthly_payment', payment.id, {'by': user.id, 'reason': obs})
            flash('Pago marcado con observaciones.', 'warning')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('payments.bandeja'))


# =============================================================================
# VALIDACIÓN DE INFORME (subir PDF de informe)
# =============================================================================
@payments_bp.route('/contract/<int:contract_id>/validate', methods=['GET', 'POST'])
@login_required
def validate_report(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    pdf_url = None
    extracted_text = ""

    if request.method == 'POST':
        if 'report_file' not in request.files:
            flash('No se adjuntó ningún archivo.', 'danger')
            return redirect(request.url)
        file = request.files['report_file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo.', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(f"informe_ct_{contract.id}_{file.filename}")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            pdf_url = url_for('static', filename=f'uploads/{filename}')
            try:
                extracted_text = extract_text_from_pdf(filepath)
                flash('Archivo procesado exitosamente.', 'success')
            except Exception as e:
                flash(f'Error procesando documento: {str(e)}', 'danger')
        else:
            flash('Formato no permitido.', 'warning')

    return render_template(
        'payments/split_view.html',
        contract=contract,
        pdf_url=pdf_url,
        extracted_text=extracted_text
    )