# app/routes/dashboard.py
from flask import Blueprint, render_template
from app.auth.utils import login_required
from app.models.contract import Contract
from app.models.provider import ServiceProvider

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    total_contracts = Contract.query.count()
    total_providers = ServiceProvider.query.count()
    recent_contracts = Contract.query.order_by(Contract.id.desc()).limit(5).all()
    
    return render_template(
        'dashboard/index.html',
        total_contracts=total_contracts,
        total_providers=total_providers,
        recent_contracts=recent_contracts
    )