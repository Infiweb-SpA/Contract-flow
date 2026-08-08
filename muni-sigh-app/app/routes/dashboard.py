# app/routes/dashboard.py
from flask import Blueprint, render_template
from app.auth.utils import login_required, get_current_user
from app.models.contract import Contract
from app.models.provider import ServiceProvider
from app.models.payment import MonthlyPayment

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    user = get_current_user()
    total_contracts = Contract.query.count()
    total_providers = ServiceProvider.query.count()
    recent_contracts = Contract.query.order_by(Contract.id.desc()).limit(5).all()

    # Conteo de pagos según rol
    if user.role == 'JEFE_DEPTO':
        # Solo los de SU departamento que debe revisar
        pending_payments = MonthlyPayment.query.join(Contract).filter(
            Contract.department_id == user.department_id,
            MonthlyPayment.approval_status.in_(['PENDIENTE_REVISION', 'OBSERVADO'])
        ).count()
    elif user.role == 'FINANZAS_CONTROL':
        # Solo los que RRHH ya aprobó y él debe liberar
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status.in_(['APROBADO_RRHH', 'OBSERVADO'])
        ).count()
    elif user.role in ('ADMIN_RRHH', 'SUPERADMIN'):
        # ADMIN Y SUPERADMIN: visibilidad total de todo el pipeline activo
        # (todos los que no están finalizados por finanzas)
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status != 'APROBADO_FINANZAS'
        ).count()
    else:
        pending_payments = 0

    return render_template(
        'dashboard/index.html',
        total_contracts=total_contracts,
        total_providers=total_providers,
        pending_payments=pending_payments,
        recent_contracts=recent_contracts,
        user=user
    )