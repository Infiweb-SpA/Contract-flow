# app/routes/dashboard.py
from flask import Blueprint, render_template, request
from app.auth.utils import login_required, get_current_user
from app.models.contract import Contract
from app.models.provider import ServiceProvider
from app.models.payment import MonthlyPayment
from app.models.user import Department

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    user = get_current_user()

    # ── Filtro por departamento ──
    selected_dept = request.args.get('dept', '', type=str)
    departments = Department.query.filter_by(is_active=1).order_by(Department.code).all()

    # ── Query base de contratos ──
    contracts_query = Contract.query

    if selected_dept:
        try:
            dept_id = int(selected_dept)
            contracts_query = contracts_query.filter(Contract.department_id == dept_id)
        except (ValueError, TypeError):
            pass

    total_contracts = contracts_query.count()
    total_providers = ServiceProvider.query.count()
    recent_contracts = contracts_query.order_by(Contract.id.desc()).limit(50).all()

    # Conteo de pagos según rol
    if user.role == 'JEFE_DEPTO':
        pending_payments = MonthlyPayment.query.join(Contract).filter(
            Contract.department_id == user.department_id,
            MonthlyPayment.approval_status.in_(['PENDIENTE_REVISION', 'OBSERVADO'])
        ).count()
    elif user.role == 'FINANZAS_CONTROL':
        pending_payments = MonthlyPayment.query.filter(
            MonthlyPayment.approval_status.in_(['APROBADO_RRHH', 'OBSERVADO'])
        ).count()
    elif user.role in ('ADMIN_RRHH', 'SUPERADMIN'):
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
        departments=departments,
        selected_dept=selected_dept,
        user=user
    )