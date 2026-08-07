# seed.py
from datetime import date
from app import create_app, db
from app.models.user import Department, User
from app.models.provider import ServiceProvider
from app.models.contract import Contract, ContractFunction

app = create_app()

with app.app_context():
    # 1. Crear la estructura de tablas si no existen
    db.create_all()

    # 2. Crear Departamento de prueba
    dept = Department.query.filter_by(code='DIDECO').first()
    if not dept:
        dept = Department(
            code='DIDECO',
            name='Dirección de Desarrollo Comunitario',
            cost_center='CC-1001'
        )
        db.session.add(dept)
        db.session.commit()
        print("-> Departamento DIDECO creado.")

    # 3. Crear Usuario Administrador de prueba
    user = User.query.filter_by(rut='11111111-1').first()
    if not user:
        admin_user = User(
            rut='11111111-1',
            first_name='Administrador',
            last_name='SIGH-MUNI',
            email='admin@munisigh.cl',
            role='ADMIN_RRHH',
            department_id=dept.id,
            is_active=1
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("-> Usuario Administrador creado.")

    # 4. Crear un Prestador de Servicios de prueba
    provider = ServiceProvider.query.filter_by(rut='12345678-9').first()
    if not provider:
        provider = ServiceProvider(
            rut='12345678-9',
            first_name='Juan',
            paternal_last_name='Pérez',
            maternal_last_name='González',
            email='juan.perez@example.com',
            phone='+56912345678',
            address='Calle Falsa 123',
            bank_name='Banco Estado',
            account_type='Cuenta Rut',
            account_number='12345678'
        )
        db.session.add(provider)
        db.session.commit()
        print("-> Prestador de prueba creado.")

    # 5. Crear un Contrato de prueba con funciones dinámicas
    contract = Contract.query.filter_by(contract_number='CT-2026-001').first()
    if not contract:
        contract = Contract(
            provider_id=provider.id,
            department_id=dept.id,
            creation_type='CREADO',
            contract_number='CT-2026-001',
            position_title='Apoyo Técnico en Informática',
            program_name='Modernización Municipal',
            monthly_amount_gross=600000.0,
            total_contract_amount=600000.0,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 12, 31),
            status='BORRADOR'
        )
        db.session.add(contract)
        db.session.commit()

        # Funciones asociadas al contrato
        func1 = ContractFunction(
            contract_id=contract.id,
            function_order=1,
            function_description='Desarrollar y mantener módulos web para la gestión interna municipal.'
        )
        func2 = ContractFunction(
            contract_id=contract.id,
            function_order=2,
            function_description='Prestar soporte técnico y capacitación a los usuarios del departamento.'
        )
        db.session.add_all([func1, func2])
        db.session.commit()
        print("-> Contrato de prueba y funciones dinámicas creados exitosamente.")