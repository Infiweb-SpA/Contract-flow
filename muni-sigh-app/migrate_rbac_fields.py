# -*- coding: utf-8 -*-
"""
Migración idempotente para RBAC granular.
Crea tablas 'permissions' y 'role_permissions' si no existen,
inserta los permisos predeterminados y los asigna a los roles base.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'contract_flow.db')

# Permisos predeterminados: (name, description, module)
DEFAULT_PERMISSIONS = [
    # Contratos
    ('create_contract', 'Crear contratos', 'contract'),
    ('edit_contract', 'Editar contratos', 'contract'),
    ('view_contract', 'Ver contratos', 'contract'),
    ('delete_contract', 'Eliminar contratos', 'contract'),
    # Decretos
    ('create_decree', 'Crear decretos/plantillas', 'decree'),
    ('edit_decree', 'Editar decretos/plantillas', 'decree'),
    ('delete_decree', 'Eliminar decretos/plantillas', 'decree'),
    # Usuarios y roles
    ('manage_users', 'Gestionar usuarios', 'user'),
    ('manage_roles', 'Gestionar roles y permisos', 'user'),
    # Auditoría
    ('view_audit', 'Ver bitácora de auditoría', 'audit'),
]

# Permisos eliminados del sistema (limpieza idempotente)
REMOVED_PERMISSIONS = ['approve_payment_lvl1', 'approve_payment_lvl2']

# Asignación predeterminada de permisos a roles (rol -> nombres de permisos)
DEFAULT_ROLE_PERMISSIONS = {
    'SUPERADMIN': [p[0] for p in DEFAULT_PERMISSIONS],
    'ADMIN_RRHH': ['create_contract', 'edit_contract', 'view_contract', 'create_decree', 'edit_decree',
                   'manage_users', 'view_audit'],
    'JEFE_DEPTO': ['view_contract', 'edit_contract', 'view_audit'],
    'FINANZAS_CONTROL': ['view_contract', 'view_audit'],
    'AUDITOR': ['view_contract', 'view_audit'],
}


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe la base de datos: {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # 1. Crear tabla roles
    if 'roles' not in existing:
        cur.execute('''
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                is_base INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            )
        ''')
        print('  + Tabla roles creada')
    else:
        print('  = Tabla roles ya existe')

    # 2. Crear tabla permissions
    if 'permissions' not in existing:
        cur.execute('''
            CREATE TABLE permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                module VARCHAR(50)
            )
        ''')
        print('  + Tabla permissions creada')
    else:
        print('  = Tabla permissions ya existe')

    # 2. Crear tabla role_permissions
    if 'role_permissions' not in existing:
        cur.execute('''
            CREATE TABLE role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name VARCHAR(50) NOT NULL,
                permission_id INTEGER NOT NULL,
                FOREIGN KEY (permission_id) REFERENCES permissions(id),
                UNIQUE(role_name, permission_id)
            )
        ''')
        print('  + Tabla role_permissions creada')
    else:
        print('  = Tabla role_permissions ya existe')

    # 3. Limpieza: eliminar permisos removidos del sistema (pagos)
    deleted_perms = 0
    for name in REMOVED_PERMISSIONS:
        cur.execute('SELECT id FROM permissions WHERE name = ?', (name,))
        row = cur.fetchone()
        if row is not None:
            cur.execute('DELETE FROM role_permissions WHERE permission_id = ?', (row[0],))
            cur.execute('DELETE FROM permissions WHERE id = ?', (row[0],))
            deleted_perms += 1
    print(f'  - Permisos removidos (eliminados): {deleted_perms}')

    # 4. Insertar roles base + permisos predeterminados
    inserted_roles = 0
    for role_name in DEFAULT_ROLE_PERMISSIONS:
        cur.execute('SELECT 1 FROM roles WHERE name = ?', (role_name,))
        if cur.fetchone() is None:
            cur.execute('INSERT INTO roles (name, description, is_base, created_at) VALUES (?, ?, 1, datetime("now"))',
                        (role_name, f'Rol base del sistema {role_name}'))
            inserted_roles += 1
    print(f'  + Roles base insertados: {inserted_roles}')

    inserted_perms = 0
    for name, desc, module in DEFAULT_PERMISSIONS:
        cur.execute('SELECT id FROM permissions WHERE name = ?', (name,))
        if cur.fetchone() is None:
            cur.execute('INSERT INTO permissions (name, description, module) VALUES (?, ?, ?)',
                        (name, desc, module))
            inserted_perms += 1
    print(f'  + Permisos insertados: {inserted_perms}')

    # 5. Asignar permisos a roles base
    inserted_rp = 0
    for role_name, perm_names in DEFAULT_ROLE_PERMISSIONS.items():
        for pname in perm_names:
            cur.execute('SELECT p.id FROM permissions p WHERE p.name = ?', (pname,))
            row = cur.fetchone()
            if row is None:
                continue
            pid = row[0]
            cur.execute('SELECT 1 FROM role_permissions WHERE role_name = ? AND permission_id = ?',
                        (role_name, pid))
            if cur.fetchone() is None:
                cur.execute('INSERT INTO role_permissions (role_name, permission_id) VALUES (?, ?)',
                            (role_name, pid))
                inserted_rp += 1
    print(f'  + Asignaciones rol-permiso insertadas: {inserted_rp}')

    conn.commit()
    conn.close()
    print('Migración RBAC completada.')


if __name__ == '__main__':
    migrate()