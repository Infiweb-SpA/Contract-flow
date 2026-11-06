# -*- coding: utf-8 -*-
"""
Migración manual (SQLite no usa Alembic): agrega a `contracts` las columnas
de la estructura Cunco si no existen. Idempotente; puede ejecutarse varias veces.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'contract_flow.db')

COLUMNS = [
    ('provider_address',  'VARCHAR(255)'),

    ('provider_comuna',   'VARCHAR(100)'),
    ('hours_weekly',      'INTEGER'),
    ('total_amount_words',  'VARCHAR(255)'),
]


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe la base de datos: {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute('PRAGMA table_info(contracts)')}

    for name, ddl in COLUMNS:
        if name in existing:
            print(f'  = contracts.{name} ya existe (omitido)')
        else:
            cur.execute(f'ALTER TABLE contracts ADD COLUMN {name} {ddl}')
            print(f'  + contracts.{name} agregada ({ddl})')

    conn.commit()
    conn.close()
    print('Migración completada.')


if __name__ == '__main__':
    migrate()
