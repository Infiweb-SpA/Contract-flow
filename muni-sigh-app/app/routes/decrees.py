from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.auth.utils import login_required, role_required
from app.models.decree import DECREE_TYPE_LABELS, DecreeTemplate

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
@role_required('SUPERADMIN')
def index():
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
@decrees_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('SUPERADMIN')
def create():
    if request.method == 'POST':
        try:
            new_template = DecreeTemplate(
                decree_type=_validate_decree_type(request.form.get('decree_type', 'OTRO')),
                decree_number=request.form.get('decree_number', '').strip() or None,
                decree_date=_parse_decree_date(request.form.get('decree_date')),
                description=request.form.get('description', '').strip(),
                year=request.form.get('year', type=int),
                is_active=bool(request.form.get('is_active')),
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
@role_required('SUPERADMIN')
def edit(template_id):
    template = DecreeTemplate.query.get_or_404(template_id)

    if request.method == 'POST':
        try:
            template.decree_type = _validate_decree_type(request.form.get('decree_type', 'OTRO'))
            template.decree_number = request.form.get('decree_number', '').strip() or None
            template.decree_date = _parse_decree_date(request.form.get('decree_date'))
            template.description = request.form.get('description', '').strip()
            template.year = request.form.get('year', type=int)
            template.is_active = bool(request.form.get('is_active'))

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
@role_required('SUPERADMIN')
def toggle(template_id):
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
@role_required('SUPERADMIN')
def delete(template_id):
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
