from datetime import datetime
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.auth.utils import login_required, role_required, get_current_user
from app.services.otp_service import request_otp, verify_otp
from app.models.decree import DECREE_TYPE_LABELS, DecreeTemplate
from app.models.user import User

decrees_bp = Blueprint('decrees', __name__, url_prefix='/decrees')


# =============================================================================
# DATOS AÑO / VALIDACIÓN
# =============================================================================
def _prune_future_years():
    """Devuelve lista de años sugeridos para el catálogo (actual y ±3)."""
    current = datetime.now().year
    return [current + i for i in range(-3, 4)]


def _parse_decree_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    except (ValueError, TypeError):
        return None


def _validate_decree_type(decree_type):
    return decree_type if decree_type in DECREE_TYPE_LABELS else 'OTRO'


# =============================================================================
# CATÁLOGO: LISTADO
# =============================================================================
@decrees_bp.route('/')
@login_required
def index():
    current_user = get_current_user()
    if not (current_user and current_user.has_permission('create_decree', 'edit_decree', 'delete_decree', 'sign_decree')):
        flash('No tiene permisos para acceder al catálogo de decretos.', 'danger')
        return redirect(url_for('dashboard.index'))
    year_filter = request.args.get('year', type=int)
    type_filter = request.args.get('type', '').strip()

    query = DecreeTemplate.query
    if year_filter:
        query = query.filter(DecreeTemplate.year == year_filter)
    if type_filter and type_filter in DECREE_TYPE_LABELS:
        query = query.filter(DecreeTemplate.decree_type == type_filter)

    templates = query.order_by(
        DecreeTemplate.is_active.desc(),
        DecreeTemplate.year.desc(),
        DecreeTemplate.id.desc()
    ).all()

    available_types = DECREE_TYPE_LABELS
    return render_template(
        'decrees/index.html',
        templates=templates,
        available_types=available_types,
        year_filter=year_filter or '',
        type_filter=type_filter,
        available_years=_prune_future_years(),
    )


# =============================================================================
# CATÁLOGO: CREAR PLANTILLA
# =============================================================================
@decrees_bp.route('/<int:template_id>/otp/request', methods=['POST'])
@login_required
def request_decree_otp(template_id):
    template = DecreeTemplate.query.get_or_404(template_id)
    current_user = get_current_user()
    if not (current_user and current_user.role == 'ALCALDE'):
        return jsonify({'success': False, 'message': 'Solo el Alcalde puede activar decretos.'}), 403
    alcalde = User.query.filter_by(role='ALCALDE', is_active=1).first()
    if not alcalde or not alcalde.email:
        return jsonify({'success': False, 'message': 'No hay un usuario Alcalde activo con correo configurado.'}), 400
    request_uuid, code = request_otp(
        email=alcalde.email,
        purpose='DECREE_SIGN',
        entity_type='decree_template',
        entity_id=template.id,
        signer_kind='ALCALDE',
        created_by_user_id=current_user.id,
        purpose_label='activación de decreto',
    )
    if not request_uuid:
        return jsonify({'success': False, 'message': 'No se pudo generar el código.'}), 500
    masked = alcalde.email
    if '@' in masked:
        local, domain = masked.split('@', 1)
        masked = (local[:2] + '***@' + domain) if len(local) > 2 else ('***@' + domain)
    return jsonify({
        'success': True,
        'request_uuid': request_uuid,
        'email': masked,
        'expires_in': current_app.config.get('OTP_EXPIRY_MINUTES', 10) * 60,
        'message': f'Código enviado a {masked}.',
    })


@decrees_bp.route('/<int:template_id>/activate', methods=['GET'])
@login_required
def activate_page(template_id):
    template = DecreeTemplate.query.get_or_404(template_id)
    current_user = get_current_user()
    if not (current_user and current_user.role == 'ALCALDE'):
        flash('Solo el Alcalde puede activar decretos.', 'danger')
        return redirect(url_for('decrees.index'))
    return render_template('decrees/activate.html', template=template)


@decrees_bp.route('/<int:template_id>/activate', methods=['POST'])
@login_required
def activate(template_id):
    template = DecreeTemplate.query.get_or_404(template_id)
    current_user = get_current_user()
    if not (current_user and current_user.role == 'ALCALDE'):
        flash('Solo el Alcalde puede activar decretos.', 'danger')
        return redirect(url_for('decrees.index'))

    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    signature = (data.get('signature') or data.get('signature_image') or data.get('signature_data') or '').strip()
    request_uuid = (data.get('request_uuid') or data.get('otp_request_uuid') or '').strip()
    otp_code = (data.get('otp_code') or data.get('code') or '').strip()

    if not signature:
        return jsonify({'success': False, 'message': 'Por favor ingresar firma.'}), 400
    if not request_uuid or not otp_code:
        return jsonify({'success': False, 'message': 'Se requiere código de verificación (OTP).'}), 400

    ok, vc, err = verify_otp(request_uuid, otp_code)
    if not ok:
        return jsonify({'success': False, 'message': err or 'Código inválido.'}), 400

    alcalde = User.query.filter_by(role='ALCALDE', is_active=1).first()
    if not alcalde:
        return jsonify({'success': False, 'message': 'No hay un usuario Alcalde activo.'}), 400
    if not vc or vc.purpose != 'DECREE_SIGN' or vc.entity_type != 'decree_template' or vc.entity_id != template.id:
        return jsonify({'success': False, 'message': 'El código no corresponde a este decreto.'}), 400
    if (vc.email or '').lower() != (alcalde.email or '').lower():
        return jsonify({'success': False, 'message': 'El código no corresponde al Alcalde.'}), 400

    MAX_SIG_LEN = 300000
    template.mayor_signature = signature[:MAX_SIG_LEN]
    template.signed_by_user_id = alcalde.id
    template.validation_code = 'DC-' + uuid.uuid4().hex[:12].upper()
    template.signed_at = datetime.utcnow()
    template.is_active = True
    db.session.commit()

    try:
        from app.services.audit_service import log_action
        log_action('DECREE_ACTIVATED', 'decree_template', template.id, {
            'decree_number': template.decree_number,
            'validation_code': template.validation_code,
        })
    except Exception:
        pass

    return jsonify({
        'success': True,
        'message': 'Decreto activado exitosamente.',
        'validation_code': template.validation_code,
    })


@decrees_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    current_user = get_current_user()
    if not (current_user and current_user.has_permission('create_decree')):
        flash('No tiene permiso para crear decretos.', 'danger')
        return redirect(url_for('decrees.index'))
    if request.method == 'POST':
        try:
            current_user = get_current_user()
            if current_user and current_user.role == 'ALCALDE':
                is_active_val = bool(request.form.get('is_active'))
            else:
                is_active_val = False

            new_template = DecreeTemplate(
                decree_type=_validate_decree_type(request.form.get('decree_type', 'OTRO')),
                decree_number=request.form.get('decree_number', '').strip() or None,
                decree_date=_parse_decree_date(request.form.get('decree_date')),
                description=request.form.get('description', '').strip(),
                year=request.form.get('year', type=int),
                is_active=is_active_val,
            )

            if not new_template.description:
                flash('El texto del VISTO es obligatorio.', 'danger')
                return redirect(url_for('decrees.create'))

            db.session.add(new_template)
            db.session.commit()

            from app.services.audit_service import log_action
            log_action(
                action='DECREE_TEMPLATE_CREATE',
                entity_type='decree_template',
                entity_id=new_template.id,
                payload={
                    'decree_number': new_template.decree_number,
                    'decree_type': new_template.decree_type,
                    'year': new_template.year,
                }
            )

            flash('Plantilla de decreto registrada exitosamente.', 'success')
            return redirect(url_for('decrees.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear plantilla: {str(e)}', 'danger')

    return render_template(
        'decrees/form.html',
        template=None,
        available_types=DECREE_TYPE_LABELS,
        available_years=_prune_future_years(),
    )


# =============================================================================
# CATÁLOGO: EDITAR PLANTILLA
# =============================================================================
@decrees_bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(template_id):
    current_user = get_current_user()
    if not (current_user and current_user.has_permission('edit_decree')):
        flash('No tiene permiso para editar decretos.', 'danger')
        return redirect(url_for('decrees.index'))
    template = DecreeTemplate.query.get_or_404(template_id)

    if request.method == 'POST':
        try:
            current_user = get_current_user()
            if current_user and current_user.role == 'ALCALDE':
                is_active_val = bool(request.form.get('is_active'))
            elif 'is_active' in request.form:
                is_active_val = bool(request.form.get('is_active'))
            else:
                is_active_val = bool(template.is_active)

            template.decree_type = _validate_decree_type(request.form.get('decree_type', 'OTRO'))
            template.decree_number = request.form.get('decree_number', '').strip() or None
            template.decree_date = _parse_decree_date(request.form.get('decree_date'))
            template.description = request.form.get('description', '').strip()
            template.year = request.form.get('year', type=int)
            template.is_active = is_active_val

            if not template.description:
                flash('El texto del VISTO es obligatorio.', 'danger')
                return redirect(request.url)

            db.session.commit()

            from app.services.audit_service import log_action
            log_action(
                action='DECREE_TEMPLATE_UPDATE',
                entity_type='decree_template',
                entity_id=template.id,
                payload={'decree_number': template.decree_number, 'decree_type': template.decree_type}
            )

            flash('Plantilla actualizada exitosamente.', 'success')
            return redirect(url_for('decrees.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar plantilla: {str(e)}', 'danger')

    return render_template(
        'decrees/form.html',
        template=template,
        available_types=DECREE_TYPE_LABELS,
        available_years=_prune_future_years(),
    )


# =============================================================================
# CATÁLOGO: ACTIVAR / DESACTIVAR
# =============================================================================
@decrees_bp.route('/<int:template_id>/toggle', methods=['POST'])
@login_required
def toggle(template_id):
    current_user = get_current_user()
    if not (current_user and current_user.role == 'ALCALDE'):
        flash('Solo el Alcalde puede activar o desactivar decretos.', 'danger')
        return redirect(url_for('decrees.index'))
    template = DecreeTemplate.query.get_or_404(template_id)
    template.is_active = not template.is_active
    db.session.commit()

    from app.services.audit_service import log_action
    log_action(
        action='DECREE_TEMPLATE_UPDATE',
        entity_type='decree_template',
        entity_id=template.id,
        payload={'decree_number': template.decree_number,
                 'decree_type': template.decree_type,
                 'is_active': template.is_active}
    )

    state = 'activada' if template.is_active else 'desactivada'
    flash(f'Plantilla {state}. Los contratos existentes no se modifican.', 'success')
    return redirect(url_for('decrees.index'))


# =============================================================================
# CATÁLOGO: ELIMINAR
# =============================================================================
@decrees_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    current_user = get_current_user()
    if not (current_user and current_user.has_permission('delete_decree')):
        flash('No tiene permiso para eliminar decretos.', 'danger')
        return redirect(url_for('decrees.index'))
    template = DecreeTemplate.query.get_or_404(template_id)

    payload = {
        'decree_number': template.decree_number,
        'decree_type': template.decree_type,
    }

    try:
        db.session.delete(template)
        db.session.commit()

        from app.services.audit_service import log_action
        log_action(action='DECREE_TEMPLATE_DELETE', entity_type='decree_template',
                   entity_id=template_id, payload=payload)

        flash('Plantilla eliminada del catálogo.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar plantilla: {str(e)}', 'danger')

    return redirect(url_for('decrees.index'))
