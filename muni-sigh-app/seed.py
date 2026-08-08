# seed.py
from datetime import date
from app import create_app, db
from app.models.user import Department, User
from app.models.provider import ServiceProvider
from app.models.contract import Contract, ContractFunction
from app.models.payment import MonthlyPayment, PaymentFunctionChecklist

app = create_app()

with app.app_context():
    # 1. Crear la estructura de tablas si no existen
    db.create_all()

    # ============================================================
    # DEPARTAMENTOS
    # ============================================================
    depts_data = [
        ('DIDECO', 'Dirección de Desarrollo Comunitario', 'CC-1001'),
        ('SECPLA', 'Secretaría de Planificación', 'CC-1002'),
        ('DOM', 'Dirección de Obras Municipales', 'CC-1003'),
    ]
    departments = {}
    for code, name, cc in depts_data:
        dept = Department.query.filter_by(code=code).first()
        if not dept:
            dept = Department(code=code, name=name, cost_center=cc)
            db.session.add(dept)
            db.session.commit()
            print(f"-> Departamento {code} creado.")
        departments[code] = dept

    # ============================================================
    # USUARIOS (todos los roles para probar el circuito completo)
    # ============================================================
    users_data = [
        {
            'rut': '11111111-1',
            'first_name': 'Administrador',
            'last_name': 'SIGH-MUNI',
            'email': 'admin@munisigh.cl',
            'role': 'ADMIN_RRHH',
            'dept_code': 'DIDECO',
            'password': 'admin123'
        },
        {
            'rut': '22222222-2',
            'first_name': 'Juan',
            'last_name': 'Martínez Jefe',
            'email': 'jefe@munisigh.cl',
            'role': 'JEFE_DEPTO',
            'dept_code': 'DIDECO',
            'password': 'jefe123'
        },
        {
            'rut': '33333333-3',
            'first_name': 'María',
            'last_name': 'López Finanzas',
            'email': 'finanzas@munisigh.cl',
            'role': 'FINANZAS_CONTROL',
            'dept_code': 'SECPLA',
            'password': 'finanzas123'
        },
        {
            'rut': '44444444-4',
            'first_name': 'Super',
            'last_name': 'Admin Root',
            'email': 'super@munisigh.cl',
            'role': 'SUPERADMIN',
            'dept_code': 'DIDECO',
            'password': 'super123'
        },
    ]

    for u_data in users_data:
        user = User.query.filter_by(rut=u_data['rut']).first()
        if not user:
            user = User(
                rut=u_data['rut'],
                first_name=u_data['first_name'],
                last_name=u_data['last_name'],
                email=u_data['email'],
                role=u_data['role'],
                department_id=departments[u_data['dept_code']].id,
                is_active=1
            )
            user.set_password(u_data['password'])
            db.session.add(user)
            db.session.commit()
            print(f"-> Usuario {u_data['role']} ({u_data['email']}) creado.")

    # ============================================================
    # PRESTADORES
    # ============================================================
    providers_data = [
        {
            'rut': '12345678-9',
            'first_name': 'Juan',
            'paternal_last_name': 'Pérez',
            'maternal_last_name': 'González',
            'email': 'juan.perez@example.com',
            'phone': '+56912345678',
            'address': 'Calle Falsa 123',
            'bank_name': 'Banco Estado',
            'account_type': 'Cuenta Rut',
            'account_number': '12345678'
        },
        {
            'rut': '98765432-1',
            'first_name': 'Ana',
            'paternal_last_name': 'Silva',
            'maternal_last_name': 'Rojas',
            'email': 'ana.silva@example.com',
            'phone': '+56987654321',
            'address': 'Av. Libertad 456',
            'bank_name': 'Banco Santander',
            'account_type': 'Cuenta Corriente',
            'account_number': '0098765432'
        },
    ]

    providers = {}
    for p_data in providers_data:
        provider = ServiceProvider.query.filter_by(rut=p_data['rut']).first()
        if not provider:
            provider = ServiceProvider(**p_data)
            db.session.add(provider)
            db.session.commit()
            print(f"-> Prestador {p_data['first_name']} {p_data['paternal_last_name']} creado.")
        providers[p_data['rut']] = provider

    # ============================================================
    # CONTRATO 1: Técnico en Informática (CT-2026-001)
    # ============================================================
    contract1 = Contract.query.filter_by(contract_number='CT-2026-001').first()
    if not contract1:
        contract1 = Contract(
            provider_id=providers['98765432-1'].id,
            department_id=departments['SECPLA'].id,
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
        db.session.add(contract1)
        db.session.commit()

        funcs_tecnico = [
            'Desarrollar y mantener módulos web para la gestión interna municipal.',
            'Prestar soporte técnico y capacitación a los usuarios del departamento.',
            'Gestionar respaldos de información y seguridad de sistemas.',
        ]
        for idx, desc in enumerate(funcs_tecnico, start=1):
            db.session.add(ContractFunction(
                contract_id=contract1.id,
                function_order=idx,
                function_description=desc,
                is_mandatory_for_payment=1
            ))
        db.session.commit()
        print("-> Contrato CT-2026-001 (Técnico) y funciones creados.")

    # ============================================================
    # CONTRATO 2: Personal de Aseo (CT-2026-0809) — El de tus screenshots
    # ============================================================
    contract2 = Contract.query.filter_by(contract_number='CT-2026-0809').first()
    if not contract2:
        contract2 = Contract(
            provider_id=providers['12345678-9'].id,
            department_id=departments['DIDECO'].id,
            creation_type='CREADO',
            contract_number='CT-2026-0809',
            decline_number='DEC-1044',
            decline_date=date(2026, 8, 7),
            position_title='Personal de aseo',
            program_name='Adulto mayor',
            monthly_amount_gross=550000.0,
            total_contract_amount=550000.0,
            start_date=date(2026, 8, 7),
            end_date=date(2026, 9, 7),
            status='EN_EJECUCION'
        )
        db.session.add(contract2)
        db.session.commit()

        funcs_aseo = [
            'Aseo de áreas comunes',
            'Limpieza de vidrios',
            'Limpieza de baños',
            'Reparación y cambios de focos',
        ]
        for idx, desc in enumerate(funcs_aseo, start=1):
            db.session.add(ContractFunction(
                contract_id=contract2.id,
                function_order=idx,
                function_description=desc,
                is_mandatory_for_payment=1
            ))
        db.session.commit()
        print("-> Contrato CT-2026-0809 (Aseo) y funciones creados.")

    # ============================================================
    # PAGO MENSUAL DE PRUEBA (para el contrato de aseo)
    # ============================================================
    payment = MonthlyPayment.query.filter_by(contract_id=contract2.id, payment_year=2026, payment_month=8).first()
    if not payment:
        payment = MonthlyPayment(
            contract_id=contract2.id,
            payment_year=2026,
            payment_month=8,
            amount_to_pay=550000.0,
            approval_status='PENDIENTE_REVISION'
        )
        db.session.add(payment)
        db.session.flush()

        # Crear checklist automático
        for func in contract2.functions:
            db.session.add(PaymentFunctionChecklist(
                monthly_payment_id=payment.id,
                contract_function_id=func.id,
                status='CUMPLIDO',
                comments=''
            ))
        db.session.commit()
        print("-> Pago mensual 08/2026 para CT-2026-0809 creado con checklist.")

    print("\n✅ Seed completado. Datos de prueba listos.")
    print("\n--- CREDENCIALES DE PRUEBA ---")
    print("ADMIN_RRHH:   admin@munisigh.cl     / admin123")
    print("JEFE_DEPTO:   jefe@munisigh.cl      / jefe123")
    print("FINANZAS:     finanzas@munisigh.cl  / finanzas123")
    print("SUPERADMIN:   super@munisigh.cl     / super123")