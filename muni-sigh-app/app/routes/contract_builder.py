# app/routes/contract_builder.py
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.auth.utils import login_required, role_required
from app.models.user import Department
from app.models.provider import ServiceProvider
from app.models.contract import Contract, ContractFunction
from app.services.audit_service import log_action
from app.services.pdf_generator import generate_contract_html

contract_builder_bp = Blueprint('contract_builder', __name__, url_prefix='/contracts')

@contract_builder_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN_RRHH', 'SUPERADMIN', 'JEFE_DEPTO')
def create():
    if request.method == 'POST':
        try:
            # Datos principales
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

            # Crear contrato en estado BORRADOR
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
            db.session.flush()  # Obtener ID generado

            # Lista de funciones dinámicas
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

            # Registro de bitácora
            log_action(
                action='CONTRACT_CREATE',
                entity_type='contract',
                entity_id=new_contract.id,
                payload={'contract_number': contract_number, 'provider_id': provider_id}
            )

            flash(f'Contrato N° {contract_number} creado exitosamente.', 'success')
            return redirect(url_for('contract_builder.preview', contract_id=new_contract.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al armar el contrato: {str(e)}', 'danger')

    providers = ServiceProvider.query.order_by(ServiceProvider.paternal_last_name).all()
    departments = Department.query.filter_by(is_active=1).all()

    return render_template('contracts/create.html', providers=providers, departments=departments)


@contract_builder_bp.route('/api/search-provider', methods=['GET'])
@login_required
def search_provider():
    """API para buscar prestadores por RUT o nombre para renovación rápida."""
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
    """Ruta AJAX para la creación rápida de prestadores dentro del armador."""
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


@contract_builder_bp.route('/<int:contract_id>/preview')
@login_required
def preview(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    return generate_contract_html(contract)