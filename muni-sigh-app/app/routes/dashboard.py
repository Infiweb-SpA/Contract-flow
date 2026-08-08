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

    # Conteo de pagos pendientes según rol
    pending_payments = 0
    if user.role == 'JEFE_DEPTO':
        pending_payments = MonthlyPayment.query.join(Contract).filter(
            Contract.department_id == user.department_id,
            MonthlyPayment.approval_status.in_(['PENDIENTE_REVISION', 'OBSERVADO'])
        ).count()
    elif user.role == 'ADMIN_RRHH':
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status.in_(['VISADO_JEFE_DEPTO', 'OBSERVADO'])
        ).count()
    elif user.role == 'FINANZAS_CONTROL':
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status.in_(['APROBADO_RRHH', 'OBSERVADO'])
        ).count()
    else:
        # SUPERADMIN ve todo lo no finalizado
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status != 'APROBADO_FINANZAS'
        ).count()

    return render_template(
        'dashboard/index.html',
        total_contracts=total_contracts,
        total_providers=total_providers,
        pending_payments=pending_payments,
        recent_contracts=recent_contracts,
        user=user
    )