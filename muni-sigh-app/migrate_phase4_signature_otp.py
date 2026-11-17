# -*- coding: utf-8 -*-
"""
Migración idempotente Fase 4: OTP para firma digital.
Agrega columnas a contract_signatures y crea verification_codes si no existen.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'contract_flow.db')


def _columns(cur, table):
    return {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: no existe la base de datos: {DB_PATH}')
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    existing = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # 1. Crear verification_codes si no existe
    if 'verification_codes' not in existing:
        cur.execute('''
            CREATE TABLE verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_uuid VARCHAR(36) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL,
                code_hash VARCHAR(255) NOT NULL,
                purpose VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50),
                entity_id INTEGER,
                signer_kind VARCHAR(30),
                created_by_user_id INTEGER,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 5,
                is_valid INTEGER NOT NULL DEFAULT 1,
                ip_address VARCHAR(64),
                user_agent TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        print('  + Tabla verification_codes creada')
    else:
        print('  = Tabla verification_codes ya existe')

    # 2. Agregar columnas a contract_signatures
    if 'contract_signatures' in existing:
        cols = _columns(cur, 'contract_signatures')
        new_cols = [
            ('operator_user_id', 'INTEGER'),
            ('signer_kind', 'VARCHAR(20)'),
            ('provider_id', 'INTEGER'),
            ('signer_email', 'VARCHAR(120)'),
            ('verification_code_id', 'INTEGER'),
            ('otp_verified_at', 'DATETIME'),
        ]
        for name, typ in new_cols:
            if name not in cols:
                cur.execute(f'ALTER TABLE contract_signatures ADD COLUMN {name} {typ}')
                print(f'  + Columna contract_signatures.{name} agregada')
            else:
                print(f'  = Columna contract_signatures.{name} ya existe')

    conn.commit()
    conn.close()
    print('Migración Fase 4 (OTP) completada.')


if __name__ == '__main__':
    migrate()