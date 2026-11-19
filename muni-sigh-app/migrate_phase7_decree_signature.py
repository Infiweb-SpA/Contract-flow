# -*- coding: utf-8 -*-
"""
Migración idempotente Fase 7: firma del Alcalde para activación de decretos.
Agrega columnas a decree_templates.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'contract_flow.db')


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe la base de datos: {DB_PATH}')
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'decree_templates' not in existing:
        print('ERROR: tabla decree_templates no existe')
        conn.close()
        return
    cols = {row[1] for row in cur.execute("PRAGMA table_info(decree_templates)")}
    new_cols = [
        ('mayor_signature', 'TEXT'),
        ('signed_by_user_id', 'INTEGER'),
        ('validation_code', 'VARCHAR(64)'),
        ('signed_at', 'DATETIME'),
    ]
    for name, typ in new_cols:
        if name not in cols:
            cur.execute(f'ALTER TABLE decree_templates ADD COLUMN {name} {typ}')
            print(f'  + Columna decree_templates.{name} agregada')
        else:
            print(f'  = Columna decree_templates.{name} ya existe')

    # is_active default: asegurar que exista (ya existe en el esquema)
    conn.commit()
    conn.close()
    print('Migración Fase 7 (firma de decretos) completada.')


if __name__ == '__main__':
    migrate()