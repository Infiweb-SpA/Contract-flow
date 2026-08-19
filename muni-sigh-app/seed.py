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
            'email': 'admin@muni.cl',
            'role': 'ADMIN_RRHH',
            'dept_code': 'DIDECO',
            'password': 'admin123'
        },
        {
            'rut': '22222222-2',
            'first_name': 'Juan',
            'last_name': 'Martínez Jefe',
            'email': 'jefe@muni.cl',
            'role': 'JEFE_DEPTO',
            'dept_code': 'DIDECO',
            'password': 'jefe123'
        },
        {
            'rut': '33333333-3',
            'first_name': 'Patricia',
            'last_name': 'Muñoz Auditora',
            'email': 'auditor@muni.cl',
            'role': 'AUDITOR',
            'dept_code': 'SECPLA',
            'password': 'auditor123'
        },
        {
            'rut': '44444444-4',
            'first_name': 'Super',
            'last_name': 'Admin Root',
            'email': 'super@muni.cl',
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
    # PRESTADORES (con nuevos campos personales)
    # ============================================================
    providers_data = [
        {
            'rut': '12345678-9',
            'first_name': 'Juan',
            'paternal_last_name': 'Pérez',
            'maternal_last_name': 'González',
            'email': 'juan.perez@example.com',
            'phone': '+56912345678',
            'address': 'Calle Falsa 123, Freire',
            'profession_or_trade': 'Técnico en Informática',
            'nationality': 'Chilena',
            'civil_status': 'Soltero',
            'birth_date': date(1990, 5, 15),
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
            'address': 'Av. Libertad 456, Freire',
            'profession_or_trade': 'Ingeniera en Informática',
            'nationality': 'Chilena',
            'civil_status': 'Casada',
            'birth_date': date(1988, 11, 22),
            'bank_name': 'Banco Santander',
            'account_type': 'Cuenta Corriente',
            'account_number': '0098765432'
        },
        {
            # Prestador del contrato de referencia (Freire)
            'rut': '18.195.673-9',
            'first_name': 'Jocelyn del Carmen',
            'paternal_last_name': 'Jara',
            'maternal_last_name': 'Huenul',
            'email': 'jocelyn.jara@example.com',
            'phone': '+56955512345',
            'address': 'Sector El Cohíche Km 7, Freire',
            'profession_or_trade': 'Fonoaudiología',
            'nationality': 'Chilena',
            'civil_status': 'Soltera',
            'birth_date': date(1992, 4, 27),
            'bank_name': 'Banco Estado',
            'account_type': 'Cuenta Corriente',
            'account_number': '5551234567'
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
            decline_number='DEC-0890',
            decline_date=date(2026, 2, 25),
            position_title='Apoyo Técnico en Informática',
            program_name='Modernización Municipal',
            monthly_amount_gross=600000.0,
            total_contract_amount=6000000.0,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 12, 31),
            contract_date=date(2026, 2, 25),
            budget_account='215.21.04.001',
            sub_program='SP 01',
            cost_center='02.01.01',
            payment_modality='MENSUAL_FIJO',
            status='EN_EJECUCION'
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
                function_description=desc
            ))
        db.session.commit()
        print("-> Contrato CT-2026-001 (Técnico) y funciones creados.")

    # ============================================================
    # CONTRATO 2: Personal de Aseo (CT-2026-0809)
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
            program_name='Adulto Mayor',
            monthly_amount_gross=550000.0,
            total_contract_amount=550000.0,
            start_date=date(2026, 8, 7),
            end_date=date(2026, 9, 7),
            contract_date=date(2026, 8, 7),
            budget_account='215.21.04.004',
            sub_program='SP 04',
            cost_center='04.01.08',
            payment_modality='MENSUAL_FIJO',
            status='EN_EJECUCION'
        )
        db.session.add(contract2)
        db.session.commit()

        funcs_aseo = [
            'Aseo de áreas comunes del establecimiento municipal.',
            'Limpieza de vidrios y superficies interiores.',
            'Limpieza y desinfección de baños.',
            'Reparación y cambio de focos y luminarias.',
        ]
        for idx, desc in enumerate(funcs_aseo, start=1):
            db.session.add(ContractFunction(
                contract_id=contract2.id,
                function_order=idx,
                function_description=desc
            ))
        db.session.commit()
        print("-> Contrato CT-2026-0809 (Aseo) y funciones creados.")

    # ============================================================
    # CONTRATO 3: Fonoaudióloga — Adulto Mayor (CT-2026-0170)
    # Basado en el contrato de referencia de la Municipalidad de Freire
    # ============================================================
    contract3 = Contract.query.filter_by(contract_number='CT-2026-0170').first()
    if not contract3:
        contract3 = Contract(
            provider_id=providers['18.195.673-9'].id,
            department_id=departments['DIDECO'].id,
            creation_type='CREADO',
            contract_number='CT-2026-0170',
            decline_number='1780',
            decline_date=date(2026, 6, 19),
            position_title='Fonoaudióloga — Programa Adulto Mayor',
            program_name='Adulto Mayor',
            monthly_amount_gross=884000.0,
            total_contract_amount=5304000.0,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 12, 31),
            contract_date=date(2026, 6, 19),
            budget_account='215.21.04.004',
            sub_program='SP 04',
            cost_center='04.01.08',
            payment_modality='POR_PRODUCTO',
            status='CREADO_PARA_FIRMA'
        )
        db.session.add(contract3)
        db.session.commit()

        funcs_fono = [
            'Realizar al menos 15 talleres mensuales relacionados a habilidades cognitivas, habilidades verbales, lenguaje, habla, voz y audición, y de deglutición, dirigidos a personas mayores de la comuna.',
            'Realizar al menos 1 material de difusión con temáticas afines a los talleres realizados de tipo informativo (díptico, tríptico o folleto).',
            'Realizar 10 evaluaciones auditivas mediante otoscopia y derivar en caso de observar hallazgos anormales.',
            'Participar en al menos 1 reunión de equipo del programa Adulto Mayor.',
        ]
        for idx, desc in enumerate(funcs_fono, start=1):
            db.session.add(ContractFunction(
                contract_id=contract3.id,
                function_order=idx,
                function_description=desc
            ))
        db.session.commit()
        print("-> Contrato CT-2026-0170 (Fonoaudiología) y funciones creados.")

    print("\n✅ Seed completado. Datos de prueba listos.")
    print("\n--- CREDENCIALES DE PRUEBA ---")
    print("ADMIN_RRHH:   admin@muni.cl   / admin123")
    print("JEFE_DEPTO:   jefe@muni.cl    / jefe123")
    print("AUDITOR:      auditor@muni.cl / auditor123")
    print("SUPERADMIN:   super@muni.cl   / super123")